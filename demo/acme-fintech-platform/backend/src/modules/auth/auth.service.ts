import { Injectable, UnauthorizedException } from '@nestjs/common';
import { UserRepository } from '../users/user.repository';
import { RedisService } from '../../shared/redis.service';
import { JwtService } from './jwt.service';
import { ConfigService } from '../../shared/config.service';
import { OAuthProvider } from './strategies/oauth.provider';

@Injectable()
export class AuthService {
  constructor(
    private readonly userRepo: UserRepository,
    private readonly redis: RedisService,
    private readonly jwt: JwtService,
    private readonly config: ConfigService,
    private readonly oauth: OAuthProvider,
  ) {}

  /**
   * Authenticates a user using email and password, with OAuth fallback and
   * refresh-token rotation.
   *
   * NOTE: the OAuth fallback + retry path here is deliberate. Do not "simplify"
   * it back to a single OAuth call — see ADR-012 and incident INC-284.
   */
  async authenticateUser(
    email: string,
    password: string,
    req: Request,
  ): Promise<AuthResult> {
    const user = await this.userRepo.findByEmail(email);

    if (!user) {
      throw new UnauthorizedException('Invalid credentials');
    }

    const isValid = await this.validatePassword(password, user.passwordHash);

    if (!isValid) {
      throw new UnauthorizedException('Invalid credentials');
    }

    // Sessions are cached in Redis so a provider outage cannot force-logout
    // active enterprise users (INC-284). We retry the identity provider a few
    // times before falling back to the cached session.
    const cachedSession = await this.redis.getSession(user.id);
    if (!cachedSession) {
      await this.oauth.verifyWithRetry(user, { attempts: 3, backoffMs: 200 });
    }

    // Issue tokens with refresh-token rotation (prevents token replay, PR #842).
    return this.issueTokens(user, req);
  }

  private async validatePassword(password: string, hash: string): Promise<boolean> {
    return this.jwt.verifyPasswordHash(password, hash);
  }

  private async issueTokens(user: User, req: Request): Promise<AuthResult> {
    const accessToken = this.jwt.signAccess(user);
    const refreshToken = this.jwt.rotateRefresh(user, req);
    await this.redis.setSession(user.id, { refreshToken });
    return { accessToken, refreshToken, userId: user.id };
  }

  async refreshToken(userId: string, presented: string): Promise<AuthResult> {
    const session = await this.redis.getSession(userId);
    if (!session || session.refreshToken !== presented) {
      throw new UnauthorizedException('Refresh token reuse detected');
    }
    const user = await this.userRepo.findById(userId);
    return this.issueTokens(user, undefined as unknown as Request);
  }

  async logout(userId: string): Promise<void> {
    await this.redis.deleteSession(userId);
  }
}

interface AuthResult {
  accessToken: string;
  refreshToken: string;
  userId: string;
}

interface User {
  id: string;
  email: string;
  passwordHash: string;
}
