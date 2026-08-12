const THEATERS = [
  { code: "0013", name: "용산아이파크몰" },
  { code: "0199", name: "천호" },
];

const MIN_REMAINING_RATIO = 0.5;
const sleep = (tab, ms) => tab.playwright.waitForTimeout(ms);

function parseSeatCount(text) {
  const normalized = String(text || "").replace(/,/g, "").replace(/\s+/g, " ");
  const fraction = normalized.match(/(\d+)\s*\/\s*(\d+)\s*석?/);
  if (fraction) return { remaining: Number(fraction[1]), total: Number(fraction[2]) };

  const remaining = normalized.match(/(?:잔여|남은)\s*(\d+)\s*석/);
  const total = normalized.match(/(?:총|전체)\s*(\d+)\s*석/);
  if (remaining && total) return { remaining: Number(remaining[1]), total: Number(total[1]) };
  return null;
}

async function timetableShows(tab, theater, watchDate) {
  const url = `https://cgv.co.kr/cnm/movieBook/cinema?siteNo=${theater.code}&siteNm=${encodeURIComponent(theater.name)}&scnYmd=${watchDate.ymd}`;
  await tab.goto(url);
  await tab.playwright.locator("body").waitFor({ state: "visible", timeoutMs: 10000 });
  // CGV renders the timetable after the document body becomes visible.
  await sleep(tab, 1800);
  const current = new URL(await tab.url());
  if (current.searchParams.get("siteNo") !== theater.code
      || current.searchParams.get("scnYmd") !== watchDate.ymd) {
    throw new Error(`scope mismatch: ${theater.code}|${watchDate.ymd}`);
  }

  const data = await tab.playwright.locator("h2").evaluateAll((headings) => {
    const movie = headings.find((heading) => {
      const title = heading.querySelector("button .title2")?.textContent;
      return (title || "").trim() === "오디세이";
    });
    if (!movie) return { shows: [] };
    const screens = [...(movie.nextElementSibling?.querySelectorAll("h3") || [])];
    const imax = screens.find((screen) => (screen.innerText || "").includes("IMAX관"));
    const list = imax?.nextElementSibling;
    const shows = [...(list?.querySelectorAll("button") || [])]
      .filter((button) => button.getAttribute("aria-disabled") !== "true")
      .map((button) => ({
        start: button.querySelector("[class*=start]")?.textContent?.trim(),
        text: button.innerText || "",
      }))
      .filter((show) => /^\d{2}:\d{2}$/.test(show.start || ""));
    return { shows };
  });

  return {
    url,
    shows: data.shows
      .filter((show) => Number(show.start.slice(0, 2)) >= watchDate.startHour)
      .map((show) => ({ ...show, seats: parseSeatCount(show.text) })),
  };
}

export async function runCgvIabMonitor(tab, watchDates, minRemainingRatio = MIN_REMAINING_RATIO) {
  const screenings = [];
  const qualifying = [];
  const errors = [];
  const schedules = [];

  for (const watchDate of watchDates) {
    for (const theater of THEATERS) {
      try {
        const schedule = await timetableShows(tab, theater, watchDate);
        schedules.push({ theater: theater.name, ymd: watchDate.ymd, count: schedule.shows.length });
        for (const show of schedule.shows) {
          if (!show.seats || show.seats.total <= 0 || show.seats.remaining > show.seats.total) {
            errors.push(`seat count missing: ${theater.code}|${watchDate.ymd}|${show.start}`);
            continue;
          }
          const item = {
            theater: theater.name,
            theaterCode: theater.code,
            ymd: watchDate.ymd,
            time: show.start,
            remaining: show.seats.remaining,
            total: show.seats.total,
            ratio: show.seats.remaining / show.seats.total,
          };
          screenings.push(item);
          if (item.ratio >= minRemainingRatio) qualifying.push(item);
        }
      } catch (error) {
        errors.push(String(error.message || error));
      }
    }
  }

  return { complete: errors.length === 0, screenings, qualifying, schedules, errors };
}
