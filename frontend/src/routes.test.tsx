import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test } from "vitest";
import { paths } from "./paths";
import { renderApp } from "./test-utils";

function tab(name: string) {
  return screen.getByRole("link", { name });
}

test("home page links to alphabet and parent screen", () => {
  renderApp(paths.home);

  expect(tab("Алфавит").getAttribute("href")).toBe(paths.alphabet);
  expect(tab("Для родителя").getAttribute("href")).toBe(paths.parent);
});

test("alphabet section opens letters tab", async () => {
  const router = renderApp(paths.home);

  await userEvent.click(tab("Алфавит"));

  expect(router.state.location.pathname).toBe(paths.letters);
  expect(tab("Буквы").getAttribute("aria-current")).toBe("page");
  expect(tab("Задания").getAttribute("aria-current")).toBeNull();
});

test("tabs switch between letters and tasks", async () => {
  const router = renderApp(paths.letters);

  await userEvent.click(tab("Задания"));

  expect(router.state.location.pathname).toBe(paths.tasks);
  expect(tab("Задания").getAttribute("aria-current")).toBe("page");
});

test("home button returns to home page", async () => {
  const router = renderApp(paths.tasks);

  await userEvent.click(tab("На главную"));

  expect(router.state.location.pathname).toBe(paths.home);
});

test("unknown address shows not found page", () => {
  renderApp("/missing");

  expect(
    screen.getByRole("heading", { name: "Страница не найдена" }),
  ).toBeTruthy();
  expect(tab("На главную").getAttribute("href")).toBe(paths.home);
});
