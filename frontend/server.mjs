import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, resolve } from "node:path";

const port = Number(process.env.PORT || 3000);
const host = "0.0.0.0";
const distDir = resolve("dist");

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
};

function resolveRequestPath(url = "/") {
  const pathname = decodeURIComponent(url.split("?")[0] || "/");
  const safePath = normalize(pathname).replace(/^(\.\.[/\\])+/, "");
  const requestedPath = resolve(join(distDir, safePath));

  if (!requestedPath.startsWith(distDir)) {
    return join(distDir, "index.html");
  }

  if (existsSync(requestedPath) && statSync(requestedPath).isFile()) {
    return requestedPath;
  }

  return join(distDir, "index.html");
}

const server = createServer((request, response) => {
  const filePath = resolveRequestPath(request.url);
  const extension = extname(filePath);

  response.setHeader("Content-Type", contentTypes[extension] || "application/octet-stream");

  if (filePath.includes(`${distDir}/assets/`)) {
    response.setHeader("Cache-Control", "public, max-age=31536000, immutable");
  } else {
    response.setHeader("Cache-Control", "no-cache");
  }

  createReadStream(filePath)
    .on("error", () => {
      response.writeHead(404);
      response.end("Not found");
    })
    .pipe(response);
});

server.listen(port, host, () => {
  console.log(`Frontend listening on ${host}:${port}`);
});
