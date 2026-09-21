# Mohit & Raja Car Deals — how to update the website

Written for someone who has never edited a website before.
You do not need to know any code. You do not need to install anything.

---

## What you will need

* A phone or a computer with internet.
* The website address: **www.mohitrajacars.com**
* One login: the Netlify account the website sits on. (Ask whoever set the
  website up for the email and password.)

---

## Adding a new car — 3 steps

### Step 1 — Open the Stock Manager

In the browser, go to:

    www.mohitrajacars.com/admin

You will see **Stock Manager** with the list of all cars currently on the website.

### Step 2 — Make your changes

* **To add a car** — press **“+ Add a car”**.
  Take a photo of the car (or pick one from the gallery), then type the make,
  model, year and price. Price is typed plainly, e.g. `21 Lakh` — the website
  adds the ₹ sign for you.
  The three short points are things like `Single Owner, 30k km, All Records`.
  Press **Save car**.

* **To remove a car that is sold** — press **Delete** next to it.

* **To change a price** — press **Edit** next to the car, change the price,
  press **Save car**.

You can add and delete as many cars as you like. Nothing on the live website
has changed yet — your changes are only saved on the phone/computer you are
using, so you can take your time.

### Step 3 — Publish

Press **Publish website** at the bottom.
A file called **mohitrajacars-website.zip** downloads.

Now put it live:

1. Open **app.netlify.com/drop** in the browser and log in.
2. Open the downloaded file so it unzips into a folder.
3. Drag that **folder** onto the big dotted box on the page.
4. Wait about a minute. Done — the new cars are live on www.mohitrajacars.com.

> Always drag the **folder**, not the zip file, and not the files inside it.

---

## Common questions

**I made a mistake and want to start over.**
Press **“Start again from the live website”** in the Stock Manager. It throws
away your unpublished changes and loads exactly what is live right now.

**I closed the page before publishing. Are my changes gone?**
No. They are remembered on that same phone/computer. Open
`www.mohitrajacars.com/admin` again and they will be there.

**Can two people edit at once?**
No — whoever publishes last wins. One person should do the daily update.

**Photos look slow / the file is very big.**
The Stock Manager already shrinks every photo you add. Nothing else to do.

**Can customers find the Stock Manager?**
It is not linked from anywhere on the website and search engines are told to
ignore it. Anyone who knows the address can open it, though, so do not share
the address publicly. (If you want it locked behind a password, that can be
switched on in Netlify under **Site settings → Access control**.)

---

## For whoever looks after this technically

* Everything Netlify publishes lives in `site/`; `netlify.toml` at the repo
  root points the build there (`base` + `publish`, no build command).
* The stock list is `site/cars.json` — a plain list of cars. Everything on the
  home page is built from it.
* Photos live in `site/assets/cars/`. A car's `photo` field may be any path or a
  full URL; when it is missing the site falls back to
  `assets/cars/<id padded to 2 digits>.jpg`.
* `site/index.html` ships with a copy of the stock list built in, so the page still
  renders a full showroom if `cars.json` ever fails to load.
* `/admin` redirects to `manager.html` (see the root `netlify.toml`).
* The Stock Manager writes new photos as `assets/cars/new-<id>.jpg` and copies
  every other file straight from the live site, so the zip it produces is a
  complete, publishable copy of the website.
