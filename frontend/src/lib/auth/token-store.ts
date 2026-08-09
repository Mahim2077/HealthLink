"use client";

type TokenListener = () => void;

export class AccessTokenStore {
  private accessToken: string | null = null;
  private generation = 0;
  private readonly listeners = new Set<TokenListener>();

  getSnapshot = (): string | null => this.accessToken;

  getServerSnapshot = (): null => null;

  getGeneration(): number {
    return this.generation;
  }

  set(token: string): void {
    this.replace(token);
  }

  clear(): void {
    const tokenChanged = this.accessToken !== null;

    this.generation += 1;
    this.accessToken = null;

    if (tokenChanged) {
      this.emit();
    }
  }

  setIfGeneration(expectedGeneration: number, token: string): boolean {
    if (this.generation !== expectedGeneration) {
      return false;
    }

    this.replace(token);
    return true;
  }

  clearIfGeneration(expectedGeneration: number): boolean {
    if (this.generation !== expectedGeneration) {
      return false;
    }

    this.clear();
    return true;
  }

  clearIfCurrent(expectedToken: string | null): boolean {
    if (this.accessToken !== expectedToken) {
      return false;
    }

    this.clear();
    return true;
  }

  subscribe = (listener: TokenListener): (() => void) => {
    this.listeners.add(listener);

    return () => {
      this.listeners.delete(listener);
    };
  };

  private emit(): void {
    this.listeners.forEach((listener) => listener());
  }

  private replace(token: string): void {
    const normalizedToken = token.trim();

    if (normalizedToken.length === 0) {
      throw new Error("Access token cannot be empty.");
    }

    const tokenChanged = normalizedToken !== this.accessToken;

    this.generation += 1;
    this.accessToken = normalizedToken;

    if (tokenChanged) {
      this.emit();
    }
  }
}

// Access tokens intentionally live only in this module-level memory store.
// Refresh tokens remain in backend-issued HttpOnly cookies.
export const accessTokenStore = new AccessTokenStore();
