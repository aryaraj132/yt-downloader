/**
 * Redis client — uses corekit's IoRedisClientService.
 * Re-exports the ioredis client for direct operations (hget, rpush, etc.).
 */
import ioRedisClient from './infra/cache/ioRedisClient';

export function getRedis() {
    return ioRedisClient;
}

export default ioRedisClient;
