import { defineConfig } from "@playwright/test";

// Dedicated ports and fixture credentials isolate automated tests from the demo DB.
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  use: {
    baseURL: "http://localhost:4318",
    viewport: { width: 1440, height: 1000 },
    ...(process.env.PLAYWRIGHT_CHROME_PATH
      ? {
          launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROME_PATH },
        }
      : {}),
  },
  webServer: [
    {
      command: "node tests/fixtures/backend.mjs",
      url: "http://127.0.0.1:4319/health",
      reuseExistingServer: false,
    },
    {
      command: "npm start -- --hostname 127.0.0.1 --port 4318",
      url: "http://localhost:4318",
      reuseExistingServer: false,
      env: {
        BACKEND_API_URL: "http://127.0.0.1:4319/api/v1",
        ADMIN_API_TOKEN: "automated-test-token-never-used-in-the-demo",
        DEMO_ADMIN_PASSWORD: "automated-test-passcode",
      },
    },
  ],
});
