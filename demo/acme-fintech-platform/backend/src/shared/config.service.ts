import { Injectable } from '@nestjs/common';

/** Central configuration accessor (env-backed). */
@Injectable()
export class ConfigService {
  get(key: string): string {
    return process.env[key] ?? '';
  }

  get redisUrl(): string {
    return this.get('REDIS_URL');
  }

  get oauthProviders(): string[] {
    return this.get('OAUTH_PROVIDERS').split(',').filter(Boolean);
  }
}
