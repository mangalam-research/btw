export class IDManager {
  private readonly ids: Record<string, boolean> = Object.create(null);
  private nextNumber: number = 0;

  constructor(private readonly prefix: string) {
  }

  generate(): string {
    let ret: string;

    do {
      ret = this.prefix + String(this.nextNumber++);
    }
    while (this.ids[ret]);

    this.ids[ret] = true;
    return ret;
  }

  seen(id: string, fail: boolean): void {
    if (id.lastIndexOf(this.prefix, 0) !== 0) {
      throw new Error(`id with incorrect prefix: ${id}`);
    }

    if (fail && this.ids[id]) {
      throw new Error(`id already seen: ${id}`);
    }

    this.ids[id] = true;
  }
}
