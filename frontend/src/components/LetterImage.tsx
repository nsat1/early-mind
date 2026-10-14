import type { LetterSummary } from "../api/letters";
import styles from "./LetterImage.module.css";

export function LetterImage({ letter }: { letter: LetterSummary }) {
  if (letter.image_url !== null) {
    return <img className={styles.image} src={letter.image_url} alt="" />;
  }
  return (
    <span className={styles.placeholder} data-kind={letter.kind}>
      <span className={styles.glyph}>
        {letter.symbol} {letter.symbol.toLocaleLowerCase("ru")}
      </span>
    </span>
  );
}
