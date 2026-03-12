from logging import getLogger

import bson
import fastapi
import pymongo
import pymongo.asynchronous.database

import app.common.tls as tls
import app.config as app_config

config = app_config.get_config()

logger = getLogger(__name__)

client: pymongo.AsyncMongoClient | None = None
db: pymongo.asynchronous.database.AsyncDatabase | None = None


async def get_mongo_client() -> pymongo.AsyncMongoClient:
    global client
    if client is None:
        # Use the custom CA Certs from env vars if set.
        # We can remove this once we migrate to mongo Atlas.
        cert = tls.custom_ca_certs.get(config.mongo_truststore)
        if cert:
            logger.info(
                "Creating MongoDB client with custom TLS cert %s",
                config.mongo_truststore,
            )
            client = pymongo.AsyncMongoClient(config.mongo_uri, tlsCAFile=cert)
        else:
            logger.info("Creating MongoDB client")
            client = pymongo.AsyncMongoClient(config.mongo_uri)

        logger.info("Testing MongoDB connection to %s", config.mongo_uri)
        await check_connection(client)
    return client


async def get_db(
    client: pymongo.AsyncMongoClient = fastapi.Depends(get_mongo_client),
) -> pymongo.asynchronous.database.AsyncDatabase:
    global db
    if db is None:
        codec_options: bson.codec_options.CodecOptions[
            dict[str, pymongo.asynchronous.database.Any]
        ] = bson.codec_options.CodecOptions(
            uuid_representation=bson.binary.UuidRepresentation.STANDARD
        )

        db = client.get_database(config.mongo_database, codec_options=codec_options)
    return db


async def check_connection(client: pymongo.AsyncMongoClient) -> None:
    database = await get_db(client)
    response = await database.command("ping")
    logger.info("MongoDB PING %s", response)
