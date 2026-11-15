// Local demonstration/testing only. PGlite is PostgreSQL compiled to WASM.
import {PGlite} from '@electric-sql/pglite';
import {PGLiteSocketServer} from '@electric-sql/pglite-socket';
const db = await PGlite.create(process.env.PGLITE_DATA_DIR || './.local-postgres');
const server = new PGLiteSocketServer({db,host:'127.0.0.1',port:Number(process.env.PGLITE_PORT || 55432)});
await server.start();
console.log('LOCAL DEMO: PostgreSQL/WASM listening on 127.0.0.1:' + (process.env.PGLITE_PORT || 55432));
for (const signal of ['SIGINT','SIGTERM']) process.on(signal,async()=>{await server.stop();await db.close();process.exit(0);});
