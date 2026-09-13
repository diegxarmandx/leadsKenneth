import { readFile, writeFile, chmod } from "node:fs/promises";
import { randomBytes } from "node:crypto";
import { parseEnv } from "node:util";

// Keep credentials in ignored local files; never echo them to the terminal.
const target = new URL("../.env.local", import.meta.url);
let contents = await readFile(target, "utf8").catch(() => "");
const current = parseEnv(contents);
const backend = parseEnv(
  await readFile(new URL("../../backend/.env", import.meta.url), "utf8"),
);
const token = current.ADMIN_API_TOKEN || backend.ADMIN_API_TOKEN;
if (!token || token.length < 32) {
  throw new Error(
    "Configure ADMIN_API_TOKEN in backend/.env before running demo:setup.",
  );
}
const defaults = {
  BACKEND_API_URL: "http://127.0.0.1:8000/api/v1",
  ADMIN_API_TOKEN: token,
  DEMO_ADMIN_PASSWORD: randomBytes(18).toString("base64url"),
};
for (const [key, value] of Object.entries(defaults)) {
  if (current[key]) continue;
  // Replace an empty example entry; preserve every existing configured value.
  contents = contents.replace(new RegExp(`^${key}=.*$`, "gm"), "");
  contents += `\n${key}=${JSON.stringify(value)}\n`;
}
await writeFile(target, contents.trim() + "\n", { mode: 0o600 });
await chmod(target, 0o600);
console.log(
  "Demo configured in frontend/.env.local. Use its DEMO_ADMIN_PASSWORD to open Operations. No credentials were printed.",
);
