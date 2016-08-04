import Promise from "bluebird";

export function waitFor(fn, delay = 100, timeout = undefined) {
  const start = Date.now();

  function check() {
    const ret = fn();
    if (ret) {
      return ret;
    }

    if ((timeout !== undefined) && (Date.now() - start > timeout)) {
      return false;
    }

    return Promise.delay(delay).then(check);
  }

  return Promise.try(check);
}
