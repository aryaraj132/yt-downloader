/**
 * IoRedis client wrapper using corekit-js IoRedisClientService.
 * Same pattern as app-backend/api/infra/cache/ioRedisClient.js
 */
import { IoRedisClientService } from '@aryaraj132/corekit-js/redisCache';
import { config } from '../../config';

const service = new IoRedisClientService(config.redisConfig.uri);
const ioRedisClient = service.getClient();

export default ioRedisClient;
export { IoRedisClientService };
