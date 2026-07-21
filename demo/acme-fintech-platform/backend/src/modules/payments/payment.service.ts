import { Injectable } from '@nestjs/common';
import { RedisService } from '../../shared/redis.service';

/**
 * Payment orchestration. Uses Redis for idempotency keys so a retried charge is
 * never double-processed — another reason Redis is load-bearing across services.
 */
@Injectable()
export class PaymentService {
  constructor(private readonly redis: RedisService) {}

  async charge(userId: string, amountCents: number, idempotencyKey: string): Promise<ChargeResult> {
    const seen = await this.redis.getSession(idempotencyKey);
    if (seen) {
      return { status: 'duplicate', userId, amountCents };
    }
    await this.redis.setSession(idempotencyKey, { refreshToken: 'charged' });
    // ... calls the payment processor
    return { status: 'ok', userId, amountCents };
  }
}

interface ChargeResult {
  status: 'ok' | 'duplicate';
  userId: string;
  amountCents: number;
}
