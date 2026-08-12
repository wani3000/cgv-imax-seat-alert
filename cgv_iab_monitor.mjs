const THEATERS = [
  { code: "0013", name: "용산아이파크몰" },
  { code: "0199", name: "천호" },
];

const sleep = (tab, ms) => tab.playwright.waitForTimeout(ms);
const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();

function adjacentPairs(available, layout, radius = 15) {
  const open = new Set(available);
  const byRow = new Map();
  for (const seat of layout) {
    const match = /^([G-J])(\d+)$/.exec(seat);
    if (!match) continue;
    const row = match[1];
    if (!byRow.has(row)) byRow.set(row, []);
    byRow.get(row).push(Number(match[2]));
  }
  const pairs = [];
  for (const [row, numbers] of byRow) {
    const center = (Math.min(...numbers) + Math.max(...numbers)) / 2;
    for (const number of numbers) {
      const next = `${row}${number + 1}`;
      if (open.has(`${row}${number}`) && open.has(next)
          && Math.abs(number - center) <= radius
          && Math.abs(number + 1 - center) <= radius) {
        pairs.push(`${row}${number}·${next}`);
      }
    }
  }
  return pairs;
}

async function timetableShows(tab, theater, watchDate) {
  const url = `https://cgv.co.kr/cnm/movieBook/cinema?siteNo=${theater.code}&siteNm=${encodeURIComponent(theater.name)}&scnYmd=${watchDate.ymd}`;
  await tab.goto(url);
  await tab.playwright.locator("h2[class*=accordion]").first().waitFor({ state: "visible", timeoutMs: 10000 });
  await sleep(tab, 300);
  const current = new URL(await tab.url());
  if (current.searchParams.get("siteNo") !== theater.code
      || current.searchParams.get("scnYmd") !== watchDate.ymd) {
    throw new Error(`scope mismatch: ${theater.code}|${watchDate.ymd}`);
  }
  const data = await tab.playwright.locator("h2").evaluateAll((headings) => {
    const movie = headings.find((h) => {
      const button = h.querySelector("button");
      const title = button?.querySelector(".title2")?.textContent;
      return (title || "").trim() === "오디세이";
    });
    if (!movie) return { opened: true, shows: [] };
    const content = movie.nextElementSibling;
    if (content) {
      const screens = [...content.querySelectorAll("h3")];
      const node = screens.find((screen) => (screen.innerText || "").includes("IMAX관"));
      if (node) {
        const list = node.nextElementSibling;
        const shows = [...(list?.querySelectorAll("button") || [])]
          .filter((button) => button.getAttribute("aria-disabled") !== "true")
          .map((button) => {
            const start = button.querySelector("[class*=start]")?.textContent?.trim();
            return { start, text: button.innerText };
          }).filter((show) => /^\d{2}:\d{2}$/.test(show.start || ""));
        return { opened: true, shows };
      }
    }
    return { opened: true, shows: [] };
  });
  data.shows = data.shows.filter((show) => Number(show.start.slice(0, 2)) >= watchDate.startHour);
  return { url, ...data };
}

async function inspectShow(tab, theater, watchDate, show) {
  const page = await timetableShows(tab, theater, watchDate);
  const movieHeading = tab.playwright.locator("h2").filter({ has: tab.playwright.locator(".title2").filter({ hasText: /^오디세이$/ }) }).first();
  const h3 = movieHeading.locator("xpath=following-sibling::div[1]//h3[contains(., 'IMAX관')]").first();
  const buttons = h3.locator("xpath=following-sibling::ul[1]//button");
  const all = await buttons.all();
  let target = null;
  for (const button of all) {
    if (clean(await button.innerText()).startsWith(show.start)) { target = button; break; }
  }
  if (!target) throw new Error(`show disappeared: ${theater.code}|${watchDate.ymd}|${show.start}`);
  await target.click();
  await tab.playwright.getByRole("heading", { name: /오디세이\(IMAX/ }).waitFor({ state: "visible", timeoutMs: 5000 });
  await sleep(tab, 700);

  const dotted = `${watchDate.ymd.slice(0, 4)}.${watchDate.ymd.slice(4, 6)}.${watchDate.ymd.slice(6, 8)}`;
  const movieOk = await tab.playwright.getByRole("heading", { name: /오디세이\(IMAX LASER 2D\)/ }).count();
  const paragraphs = await tab.playwright.locator("p").allTextContents();
  const dateOk = paragraphs.some((text) => clean(text).startsWith(`${dotted} (`));
  const theaterOk = await tab.playwright.getByText(new RegExp(`^${theater.name} IMAX관 IMAX LASER 2D$`)).count();
  if (!movieOk || !dateOk || !theaterOk) {
    throw new Error(`seat scope mismatch: ${theater.code}|${watchDate.ymd}|${show.start}`);
  }
  const selectedShow = tab.playwright.getByRole("button", { name: new RegExp(`상영 시간 ${show.start.replace(":", "\\:")}부터`) });
  if (await selectedShow.getAttribute("aria-pressed") !== "true") {
    throw new Error(`show selection mismatch: ${theater.code}|${watchDate.ymd}|${show.start}`);
  }
  const groups = await tab.playwright.getByRole("group", { name: "일반" }).all();
  if (!groups.length) throw new Error("adult selector missing");
  await groups[0].getByRole("button", { name: "2 선택" }).click();
  await sleep(tab, 180);
  const seats = await tab.playwright.locator("span[class*=seatNumber]").evaluateAll((elements) => {
    const rows = elements.map((element) => ({
      name: (element.textContent || "").trim(),
      disabled: String(element.className).includes("seatDisabled"),
    })).filter((seat) => /^[A-Z]\d+$/.test(seat.name));
    return { layout: rows.map((seat) => seat.name), available: rows.filter((seat) => !seat.disabled).map((seat) => seat.name) };
  });
  return { key: `${theater.code}|${watchDate.ymd}|${show.start}`, pairs: adjacentPairs(seats.available, seats.layout), page };
}

export async function runCgvIabMonitor(tab, watchDates) {
  const expected = new Set();
  const checked = new Set();
  const matches = [];
  const errors = [];
  const schedules = [];
  for (const watchDate of watchDates) {
    for (const theater of THEATERS) {
      try {
        const schedule = await timetableShows(tab, theater, watchDate);
        schedules.push({ theater: theater.name, ymd: watchDate.ymd, count: schedule.shows.length });
        for (const show of schedule.shows) expected.add(`${theater.code}|${watchDate.ymd}|${show.start}`);
        for (const show of schedule.shows) {
          try {
            let result;
            try {
              result = await inspectShow(tab, theater, watchDate, show);
            } catch (firstError) {
              await sleep(tab, 500);
              result = await inspectShow(tab, theater, watchDate, show);
            }
            checked.add(result.key);
            if (result.pairs.length) matches.push({ theater: theater.name, ymd: watchDate.ymd, time: show.start, pairs: result.pairs });
          } catch (error) { errors.push(String(error.message || error)); }
        }
      } catch (error) { errors.push(String(error.message || error)); }
    }
  }
  const missing = [...expected].filter((key) => !checked.has(key)).sort();
  return { complete: errors.length === 0 && missing.length === 0, expected: expected.size, checked: checked.size, missing, matches, schedules, errors };
}
