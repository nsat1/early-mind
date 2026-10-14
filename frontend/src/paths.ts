import type { LetterKind } from "./api/letters";

export const paths = {
  home: "/",
  alphabet: "/alphabet",
  letters: "/alphabet/letters",
  tasks: "/alphabet/tasks",
  parent: "/parent",
} as const;

function withKind(path: string, kind: LetterKind | undefined) {
  return kind === undefined ? path : `${path}?kind=${kind}`;
}

export function lettersPath(kind?: LetterKind) {
  return withKind(paths.letters, kind);
}

export function letterPath(code: string, kind?: LetterKind) {
  return withKind(`${paths.letters}/${code}`, kind);
}
