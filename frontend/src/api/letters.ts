import { queryOptions } from "@tanstack/react-query";
import { api } from "./client";
import type { components } from "./schema";

export type LetterKind = components["schemas"]["LetterKind"];
export type LetterSummary = components["schemas"]["LetterSummary"];

export const ALPHABET_ID = "ru";
const LETTER_KINDS: readonly LetterKind[] = ["vowel", "consonant", "sign"];

export function parseKind(value: string | null): LetterKind | undefined {
  return LETTER_KINDS.find((kind) => kind === value);
}

export function lettersQuery(kind: LetterKind | undefined) {
  return queryOptions({
    queryKey: ["letters", ALPHABET_ID, kind ?? "all"],
    queryFn: async () => {
      const { data, response } = await api.GET(
        "/api/v1/alphabets/{alphabet_id}/letters",
        { params: { path: { alphabet_id: ALPHABET_ID }, query: { kind } } },
      );
      if (data === undefined) {
        throw new Error(`Letters request failed: ${response.status}`);
      }
      return data;
    },
  });
}
