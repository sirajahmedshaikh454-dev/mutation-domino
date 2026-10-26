import { access, cp, mkdir, rm } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const source = resolve(root, 'node_modules', 'molstar', 'build', 'viewer');
const destination = resolve(root, 'public', 'molstar');

async function exists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

if (!(await exists(source))) {
  console.error('Mol* is not installed. Run "npm install" before starting the frontend.');
  process.exit(1);
}

await rm(destination, { recursive: true, force: true });
await mkdir(destination, { recursive: true });

for (const file of ['molstar.js', 'molstar.css']) {
  await cp(resolve(source, file), resolve(destination, file));
}

for (const directory of ['images', 'theme']) {
  if (await exists(resolve(source, directory))) {
    await cp(resolve(source, directory), resolve(destination, directory), { recursive: true });
  }
}

console.log('Prepared Mol* viewer assets in public/molstar.');
