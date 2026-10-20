/* Streamlit WebSocket compatibility over same-origin HTTP. Load before its bundle. */
(() => {
  const NativeWebSocket = window.WebSocket;
  const root = "/_greenhouse_transport/session";
  class HttpSocket extends EventTarget {
    static CONNECTING = 0; static OPEN = 1; static CLOSING = 2; static CLOSED = 3;
    constructor(url, protocols = []) {
      super();
      this.url = new URL(url, location.href).href;
      this.readyState = 0;
      this.protocol = "";
      this.extensions = "";
      this.binaryType = "blob";
      this.bufferedAmount = 0;
      this.pending = Promise.resolve();
      this.start(typeof protocols === "string" ? [protocols] : protocols);
    }
    emit(event) {
      this.dispatchEvent(event);
      if (typeof this["on" + event.type] === "function") this["on" + event.type](event);
    }
    async request(data, id = this.id) {
      const response = await fetch(root + (id ? "/" + id : ""), {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: {"Content-Type": "application/json", "X-Greenhouse-Transport": "1"},
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error("Streamlit HTTP transport: " + response.status);
      return response.json();
    }
    async start(protocols) {
      try {
        const session = await this.request({protocols});
        this.id = session.id;
        this.protocol = session.protocol;
        if (this.readyState !== 0) {
          await this.request({action: "close"});
          return;
        }
        this.readyState = 1;
        this.emit(new Event("open"));
        while (this.readyState === 1) {
          const result = await this.request({action: "poll"});
          if (this.readyState !== 1) break;
          for (const message of result.messages) {
            let data = message.data;
            if (message.binary) {
              const bytes = Uint8Array.from(atob(data), c => c.charCodeAt(0));
              data = this.binaryType === "arraybuffer" ? bytes.buffer : new Blob([bytes]);
            }
            this.emit(new MessageEvent("message", {data, origin: location.origin}));
          }
          if (result.closed) { this.finish(1000, "", true); break; }
        }
      } catch (error) { this.fail(error); }
    }
    send(data) {
      if (this.readyState === 0) throw new DOMException("Socket is connecting", "InvalidStateError");
      if (this.readyState !== 1) return;
      const size = typeof data === "string" ? new TextEncoder().encode(data).length : data.size ?? data.byteLength;
      this.bufferedAmount += size;
      this.pending = this.pending.then(async () => {
        const binary = typeof data !== "string";
        let encoded = data;
        if (binary) {
          const buffer = data instanceof Blob ? await data.arrayBuffer() : data;
          const bytes = ArrayBuffer.isView(buffer)
            ? new Uint8Array(buffer.buffer, buffer.byteOffset, buffer.byteLength) : new Uint8Array(buffer);
          let text = "";
          for (let offset = 0; offset < bytes.length; offset += 32768) {
            text += String.fromCharCode(...bytes.subarray(offset, offset + 32768));
          }
          encoded = btoa(text);
        }
        await this.request({action: "send", binary, data: encoded});
        this.bufferedAmount -= size;
      }).catch(error => this.fail(error));
    }
    close(code = 1000, reason = "") {
      if (this.readyState >= 2) return;
      this.readyState = 2;
      this.pending.then(() => this.id && this.request({action: "close"}))
        .catch(() => {}).finally(() => this.finish(code, reason, true));
    }
    finish(code, reason, wasClean) {
      if (this.readyState === 3) return;
      this.readyState = 3;
      this.emit(new CloseEvent("close", {code, reason, wasClean}));
    }
    fail(error) {
      if (this.readyState >= 2) return;
      console.error(error);
      this.emit(new Event("error"));
      if (this.id) this.request({action: "close"}).catch(() => {});
      this.finish(1006, "HTTP transport disconnected", false);
    }
  }
  for (const name of ["CONNECTING", "OPEN", "CLOSING", "CLOSED"]) {
    Object.defineProperty(HttpSocket.prototype, name, {value: HttpSocket[name]});
  }
  // Other WebSocket consumers retain their native transport.
  window.WebSocket = new Proxy(NativeWebSocket, {
    construct(target, args) {
      const url = new URL(args[0], location.href);
      if (url.host === location.host && url.pathname === "/_stcore/stream") {
        return new HttpSocket(...args);
      }
      return new target(...args);
    },
  });
})();
