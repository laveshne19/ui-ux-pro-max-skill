#!/usr/bin/env node
'use strict';

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const TEMPLATE_DIMS = {
  gbp:      { w: 1200, h: 900  },
  poster:   { w: 1080, h: 1350 },
  story:    { w: 1080, h: 1920 },
  festival: { w: 1080, h: 1350 },
  reel:     { w: 1080, h: 1920 },
};

const TEMPLATE_FILES = {
  gbp:      'templates/gbp_post/p.html',
  poster:   'templates/gbp_post/p.html',
  story:    'templates/gbp_post/p.html',
  festival: 'templates/festival_greeting/kc.html',
  reel:     'templates/studio_reel/v.html',
};

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i++) {
    if (argv[i].startsWith('--')) {
      const key = argv[i].slice(2);
      args[key] = (argv[i + 1] && !argv[i + 1].startsWith('--')) ? argv[++i] : true;
    }
  }
  return args;
}

function die(msg) {
  console.error('[render] ERROR:', msg);
  process.exit(1);
}

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function renderOnce(templatePath, config, brand, outFile, w, h) {
  const browser = await chromium.launch({ args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  try {
    const page = await browser.newPage();
    await page.setViewportSize({ width: w, height: h });

    const url = 'file://' + path.resolve(templatePath);
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });

    await page.evaluate(({ cfg, brnd }) => {
      window.__CONFIG__ = cfg;
      window.__BRAND__ = brnd;
      if (typeof window.__applyConfig === 'function') {
        window.__applyConfig(cfg, brnd);
      }
    }, { cfg: config, brnd: brand });

    await page.waitForTimeout(800);

    await page.screenshot({
      path: outFile,
      type: 'png',
      fullPage: false,
    });
  } finally {
    await browser.close();
  }
}

async function main() {
  const args = parseArgs(process.argv);

  if (!args.template) die('--template is required (gbp|poster|story|festival|reel)');
  if (!args.brand)    die('--brand is required (nalanda|bizwrap|cgi)');
  if (!args.config)   die('--config <file.json> is required');

  const tpl    = args.template.toLowerCase();
  const scale  = parseInt(args.scale || '2', 10);
  const outDir = args.out || 'out';
  const root   = path.dirname(path.resolve(__filename));

  if (!TEMPLATE_DIMS[tpl]) {
    die(`Unknown template "${tpl}". Choose: ${Object.keys(TEMPLATE_DIMS).join(', ')}`);
  }

  const brandsFile = path.join(root, 'brands.json');
  if (!fs.existsSync(brandsFile)) die('brands.json not found at ' + brandsFile);

  const brands = JSON.parse(fs.readFileSync(brandsFile, 'utf8'));
  const brand = brands[args.brand.toLowerCase()];
  if (!brand) {
    die(`Unknown brand "${args.brand}". Choose: ${Object.keys(brands).join(', ')}`);
  }

  const cfgPath = path.resolve(args.config);
  if (!fs.existsSync(cfgPath)) die('Config file not found: ' + cfgPath);
  const config = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));

  const templateFile = path.join(root, TEMPLATE_FILES[tpl]);
  if (!fs.existsSync(templateFile)) die('Template not found: ' + templateFile);

  const w = parseInt(args.width  || TEMPLATE_DIMS[tpl].w, 10) * scale;
  const h = parseInt(args.height || TEMPLATE_DIMS[tpl].h, 10) * scale;

  try {
    fs.mkdirSync(outDir, { recursive: true });
    fs.accessSync(outDir, fs.constants.W_OK);
  } catch (e) {
    die('Output directory is not writable: ' + outDir);
  }

  const slug = config.slug || `${tpl}-${args.brand}-${Date.now()}`;
  const outFile = path.join(outDir, slug + '.png');

  let lastErr;
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      await renderOnce(templateFile, config, brand, outFile, w, h);
      console.log('[render] Saved:', path.resolve(outFile));
      return;
    } catch (e) {
      lastErr = e;
      console.warn(`[render] Attempt ${attempt}/3 failed: ${e.message}`);
      if (attempt < 3) await sleep(attempt * 1000);
    }
  }
  die('All render attempts failed: ' + lastErr.message);
}

main().catch(e => { console.error(e); process.exit(1); });
