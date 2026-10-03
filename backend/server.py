import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError
from core import db, client, initialize, now, Document
from security import admin_user, cron_authorized, limit
from chain import rpc, signer, assert_devnet
from wallet_routes import router as wallet_router
from funds_routes import router as funds_router
from payment_service import process_payment, reconcile_deposit, PUBLIC_PROJECTION
from amounts import parse_command


@asynccontextmanager
async def lifespan(app):
    await initialize()
    yield
    client.close()


app = FastAPI(title='TIPRR — Solana devnet', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[os.environ['APP_ORIGIN']],
                   allow_credentials=True, allow_methods=['GET', 'POST'], allow_headers=['Content-Type', 'Authorization', 'X-Webhook-Id', 'X-CSRF-Token'])


@app.middleware('http')
async def protections(request: Request, call_next):
    try:
        content_length = int(request.headers.get('content-length', '0') or 0)
    except ValueError:
        return JSONResponse({'detail': 'Invalid Content-Length.'}, status_code=400)
    if content_length > 16384:
        return JSONResponse({'detail': 'Request too large.'}, status_code=413)
    origin = request.headers.get('origin')
    if request.method == 'POST' and origin and origin != os.environ['APP_ORIGIN']:
        return JSONResponse({'detail': 'Origin not allowed.'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Cache-Control'] = 'no-store'
    return response


app.include_router(wallet_router)
app.include_router(funds_router)


@app.get('/api/health')
async def health():
    await db.command('ping')
    return {'status': 'ok', 'app': 'TIPRR', 'network': 'devnet', 'mode': os.environ['BOT_MODE']}


@app.get('/api/system/status', response_model=Document)
async def system_status():
    rpc_status, rpc_error, slot = 'unavailable', None, None
    try:
        await assert_devnet()
        slot = await rpc('getSlot', [{'commitment': 'finalized'}])
        rpc_status = 'connected'
    except HTTPException as error:
        rpc_error = str(error.detail)
    try:
        treasury = str(signer().pubkey())
        signer_status = 'configured'
    except HTTPException:
        treasury, signer_status = None, 'configuration_required'
    last_job = await db.jobs.find_one({'status': 'COMPLETED'}, {'_id': 0}, sort=[('finished_at', -1)])
    return {'mode': os.environ['BOT_MODE'], 'network': os.environ['SOLANA_NETWORK'],
        'real_funds': False, 'database': 'MongoDB', 'rpc': {'status': rpc_status, 'error': rpc_error, 'slot': slot},
        'signer': {'status': signer_status, 'public_key': treasury, 'type': 'isolated_devnet'},
        'x_oauth': {'status': 'configuration_required', 'enabled': False,
                    'required': ['X_CLIENT_ID', 'X_CLIENT_SECRET', 'X_REDIRECT_URI']},
        'x_bot': {'status': 'not_enabled', 'enabled': False,
                  'required': ['Official X API access', 'X_BOT_ACCESS_TOKEN', 'X OAuth integration phase']},
        'usepaid': {'status': 'configuration_required', 'enabled': False,
                    'required': ['Official UsePaid API documentation', 'USEPAID_API_KEY', 'USEPAID_API_URL']},
        'reconciliation': {'schedule': 'Every 15 minutes', 'last_run': last_job.get('finished_at') if last_job else None},
        'checked_at': now().isoformat()}


class CommandRequest(BaseModel):
    text: str = Field(max_length=256)


@app.post('/api/tools/validate-command')
async def validate_command(body: CommandRequest, request: Request):
    await limit(f'parser:{request.client.host}', 30)
    return {**parse_command(body.text), 'executed': False}


@app.get('/api/admin/stats', response_model=Document)
async def admin_stats(user=Depends(admin_user)):
    volumes = await db.payments.aggregate([
        {'$match': {'status': 'COMPLETED', 'type': 'TIP'}},
        {'$group': {'_id': '$asset_id', 'amount_base_units': {'$sum': {'$toDecimal': '$amount_base_units'}}, 'count': {'$sum': 1}}}
    ]).to_list(500)
    return {'total_users': await db.users.count_documents({}),
            'total_deposits': await db.deposits.count_documents({'status': 'COMPLETED'}),
            'total_withdrawals': await db.payments.count_documents({'type': 'WITHDRAWAL', 'status': 'COMPLETED'}),
            'total_tips': await db.payments.count_documents({'type': 'TIP'}),
            'pending_claims': await db.pending_claims.count_documents({'status': 'PENDING'}),
            'failed_payments': await db.payments.count_documents({'status': 'FAILED'}),
            'volumes': [{'asset_id': row['_id'], 'amount_base_units': str(row['amount_base_units']), 'count': row['count']} for row in volumes],
            'recent_payments': await db.payments.find({}, PUBLIC_PROJECTION).sort('created_at', -1).to_list(50)}


class CronEnvelope(BaseModel):
    event: str = Field(pattern='^schedule.triggered$')
    run_id: str = Field(min_length=1, max_length=128)
    schedule_id: str
    dispatch_time: str


async def reconcile(run_id):
    errors = 0
    try:
        for row in await db.deposits.find({'status': 'PROCESSING'}, {'_id': 0}).limit(100).to_list(100):
            try:
                await reconcile_deposit(row)
            except Exception:
                errors += 1
        for row in await db.payments.find({'status': {'$in': ['PENDING', 'PROCESSING']}}, {'_id': 0, 'id': 1}).limit(100).to_list(100):
            try:
                await process_payment(row['id'])
            except Exception:
                errors += 1
        await db.jobs.update_one({'run_id': run_id}, {'$set': {'status': 'COMPLETED', 'errors': errors, 'finished_at': now().isoformat()}})
    except Exception:
        await db.jobs.update_one({'run_id': run_id}, {'$set': {'status': 'FAILED', 'finished_at': now().isoformat()}})


@app.post('/api/cron/reconcile')
async def cron_reconcile(request: Request, background: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    cron_authorized(request)
    try:
        body = CronEnvelope.model_validate(await request.json())
    except (ValueError, TypeError):
        raise HTTPException(400, 'Invalid schedule webhook envelope.')
    run_id = request.headers.get('x-webhook-id') or body.run_id
    try:
        await db.jobs.insert_one({'run_id': run_id, 'status': 'PENDING', 'created_at': now().isoformat()})
    except DuplicateKeyError:
        return {'accepted': True, 'duplicate': True}
    background.add_task(reconcile, run_id)
    return {'accepted': True, 'duplicate': False}
