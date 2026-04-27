const { execFileSync } = require("child_process");
const port = process.env.PORT || "3000";
execFileSync("npx", ["next", "start", "--port", port], { stdio: "inherit" });
