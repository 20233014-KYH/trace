// shadcn MCP 서버를 web/ 폴더에서 띄운다 — components.json(레지스트리: shadcn · @magicui · @react-bits)이 여기 있기 때문.
// Claude Code 의 .mcp.json 은 작업 폴더를 지정할 수 없어서 이 작은 실행기가 폴더를 옮긴 뒤 npx 를 부른다 (윈도우·맥 공통).
const { spawn } = require("node:child_process");
const path = require("node:path");
process.chdir(path.join(__dirname, ".."));
const npx = process.platform === "win32" ? "npx.cmd" : "npx";
const p = spawn(npx, ["-y", "shadcn@latest", "mcp"], { stdio: "inherit", shell: process.platform === "win32" });
p.on("exit", (code) => process.exit(code ?? 0));
