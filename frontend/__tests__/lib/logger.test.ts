import {
  getSessionCorrelationId,
  createCorrelationId,
  correlationHeaders,
  logger,
} from "../../lib/logger";

describe("logger", () => {
  beforeEach(() => {
    jest.spyOn(console, "log").mockImplementation(() => {});
    jest.spyOn(console, "warn").mockImplementation(() => {});
    jest.spyOn(console, "error").mockImplementation(() => {});
    jest.spyOn(console, "debug").mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe("getSessionCorrelationId", () => {
    it("returns a consistent ID within a session", () => {
      const id1 = getSessionCorrelationId();
      const id2 = getSessionCorrelationId();
      expect(id1).toBe(id2);
      expect(id1).toBeTruthy();
    });
  });

  describe("createCorrelationId", () => {
    it("returns a string", () => {
      const id = createCorrelationId();
      expect(typeof id).toBe("string");
      expect(id).toBeTruthy();
    });
  });

  describe("correlationHeaders", () => {
    it("returns headers with X-Correlation-Id", () => {
      const headers = correlationHeaders();
      expect(headers).toHaveProperty("X-Correlation-Id");
      expect(headers["X-Correlation-Id"]).toBeTruthy();
    });

    it("uses provided correlationId", () => {
      const headers = correlationHeaders("my-custom-id");
      expect(headers["X-Correlation-Id"]).toBe("my-custom-id");
    });
  });

  describe("logger methods", () => {
    it("logger.info outputs to console.log", () => {
      logger.info("test info");
      expect(console.log).toHaveBeenCalled();
    });

    it("logger.warn outputs to console.warn", () => {
      logger.warn("test warn");
      expect(console.warn).toHaveBeenCalled();
    });

    it("logger.error outputs to console.error", () => {
      logger.error("test error");
      expect(console.error).toHaveBeenCalled();
    });

    it("logger.debug outputs to console.debug", () => {
      logger.debug("test debug");
      expect(console.debug).toHaveBeenCalled();
    });

    it("logger.info includes context", () => {
      logger.info("with context", { key: "value" });
      expect(console.log).toHaveBeenCalled();
    });

    it("logger.error includes context", () => {
      logger.error("with context", { err: "details" });
      expect(console.error).toHaveBeenCalled();
    });

    it("logger accepts custom correlationId", () => {
      logger.info("custom id", undefined, "corr-123");
      expect(console.log).toHaveBeenCalled();
    });

    it("logger.warn with context and correlationId", () => {
      logger.warn("warn msg", { detail: 1 }, "corr-456");
      expect(console.warn).toHaveBeenCalled();
    });
  });

  describe("development mode output", () => {
    it("outputs readable format with prefix in dev", () => {
      logger.info("dev message", { detail: "test" });
      expect(console.log).toHaveBeenCalled();
      const firstArg = (console.log as jest.Mock).mock.calls[0][0];
      // In dev mode, should have [INFO] prefix with correlation ID
      expect(firstArg).toMatch(/\[INFO\]/);
    });

    it("outputs readable error with prefix in dev", () => {
      logger.error("dev error");
      expect(console.error).toHaveBeenCalled();
      const firstArg = (console.error as jest.Mock).mock.calls[0][0];
      expect(firstArg).toMatch(/\[ERROR\]/);
    });

    it("outputs readable warn with prefix in dev", () => {
      logger.warn("dev warn");
      expect(console.warn).toHaveBeenCalled();
      const firstArg = (console.warn as jest.Mock).mock.calls[0][0];
      expect(firstArg).toMatch(/\[WARN\]/);
    });

    it("outputs readable debug with prefix in dev", () => {
      logger.debug("dev debug");
      expect(console.debug).toHaveBeenCalled();
      const firstArg = (console.debug as jest.Mock).mock.calls[0][0];
      expect(firstArg).toMatch(/\[DEBUG\]/);
    });
  });
});
