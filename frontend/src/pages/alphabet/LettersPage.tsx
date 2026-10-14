import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";
import { type LetterKind, lettersQuery, parseKind } from "../../api/letters";
import { LetterImage } from "../../components/LetterImage";
import { letterPath, lettersPath } from "../../paths";
import styles from "./LettersPage.module.css";

const FILTERS: { kind?: LetterKind; sample: string; label: string }[] = [
  { sample: "А–Я", label: "Все" },
  { kind: "vowel", sample: "А", label: "Гласные" },
  { kind: "consonant", sample: "Б", label: "Согласные" },
  { kind: "sign", sample: "Ъ", label: "Знаки" },
];

export function LettersPage() {
  const [searchParams] = useSearchParams();
  const kind = parseKind(searchParams.get("kind"));
  const letters = useQuery(lettersQuery(kind));

  return (
    <>
      <h1 className={styles.title}>Буквы</h1>
      <nav className={styles.filters} aria-label="Вид букв">
        {FILTERS.map((filter) => (
          <Link
            key={filter.label}
            to={lettersPath(filter.kind)}
            className={styles.filter}
            aria-current={filter.kind === kind ? "true" : undefined}
          >
            <span
              className={styles.sample}
              data-kind={filter.kind ?? "all"}
              aria-hidden="true"
            >
              {filter.sample}
            </span>
            <span className={styles.filterLabel}>{filter.label}</span>
          </Link>
        ))}
      </nav>
      {letters.isPending && <p>Загружаем буквы…</p>}
      {letters.isError && (
        <div className={styles.error} role="alert">
          <p>Не удалось загрузить буквы</p>
          <button
            type="button"
            className={styles.retry}
            onClick={() => letters.refetch()}
          >
            Повторить
          </button>
        </div>
      )}
      {letters.isSuccess && (
        <ul className={styles.grid}>
          {letters.data.map((letter) => (
            <li key={letter.code}>
              <Link
                to={letterPath(letter.code, kind)}
                className={styles.tile}
                aria-label={letter.symbol}
              >
                <LetterImage letter={letter} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
