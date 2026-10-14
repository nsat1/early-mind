import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, type Mock, test, vi } from "vitest";
import type { LetterSummary } from "../../api/letters";
import { renderApp } from "../../test-utils";

const LETTERS: LetterSummary[] = [
  {
    code: "a",
    symbol: "А",
    kind: "vowel",
    image_url: "/media/ru/letters/a.webp?v=1a2b3c4d",
  },
  { code: "b", symbol: "Б", kind: "consonant", image_url: null },
];

type FetchMock = Mock<(request: Request) => Promise<Response>>;

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockApi(...responses: Response[]): FetchMock {
  const fetchMock: FetchMock = vi.fn();
  for (const response of responses) {
    fetchMock.mockResolvedValueOnce(response);
  }
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function requestedKinds(fetchMock: FetchMock) {
  return fetchMock.mock.calls.map(([request]) =>
    new URL(request.url).searchParams.get("kind"),
  );
}

test("letters are shown in API order with image or placeholder", async () => {
  const fetchMock = mockApi(json(LETTERS));

  renderApp("/alphabet/letters");

  const withImage = await screen.findByRole("link", { name: "А" });
  const placeholder = screen.getByRole("link", { name: "Б" });
  expect(withImage.getAttribute("href")).toBe("/alphabet/letters/a");
  expect(withImage.querySelector("img")?.getAttribute("src")).toBe(
    "/media/ru/letters/a.webp?v=1a2b3c4d",
  );
  expect(placeholder.textContent).toBe("Б б");
  expect(new URL(fetchMock.mock.calls[0]?.[0].url ?? "").pathname).toBe(
    "/api/v1/alphabets/ru/letters",
  );
  expect(requestedKinds(fetchMock)).toEqual([null]);
});

test("filter changes address and request", async () => {
  const fetchMock = mockApi(json(LETTERS), json(LETTERS.slice(0, 1)));
  const router = renderApp("/alphabet/letters");
  await screen.findByRole("link", { name: "Б" });

  await userEvent.click(screen.getByRole("link", { name: "Гласные" }));

  expect(router.state.location.search).toBe("?kind=vowel");
  expect(await screen.findByRole("link", { name: "А" })).toBeTruthy();
  expect(screen.queryByRole("link", { name: "Б" })).toBeNull();
  expect(
    screen.getByRole("link", { name: "Гласные" }).getAttribute("aria-current"),
  ).toBe("true");
  expect(requestedKinds(fetchMock)).toEqual([null, "vowel"]);
});

test("address with filter opens filtered letters", async () => {
  const fetchMock = mockApi(json(LETTERS.slice(1)));

  renderApp("/alphabet/letters?kind=consonant");

  const tile = await screen.findByRole("link", { name: "Б" });
  expect(tile.getAttribute("href")).toBe("/alphabet/letters/b?kind=consonant");
  expect(requestedKinds(fetchMock)).toEqual(["consonant"]);
});

test("unknown filter in address shows all letters", async () => {
  const fetchMock = mockApi(json(LETTERS));

  renderApp("/alphabet/letters?kind=digits");

  await screen.findByRole("link", { name: "Б" });
  expect(requestedKinds(fetchMock)).toEqual([null]);
  expect(
    screen.getByRole("link", { name: "Все" }).getAttribute("aria-current"),
  ).toBe("true");
});

test("failed request can be retried", async () => {
  mockApi(json({ detail: "Database unavailable" }, 503), json(LETTERS));
  renderApp("/alphabet/letters");

  const alert = await screen.findByRole("alert");
  expect(alert.textContent).toContain("Не удалось загрузить буквы");

  await userEvent.click(screen.getByRole("button", { name: "Повторить" }));

  expect(await screen.findByRole("link", { name: "А" })).toBeTruthy();
  expect(screen.queryByRole("alert")).toBeNull();
});
