import { Link } from "react-router";
import { paths } from "../paths";
import styles from "./HomePage.module.css";

export function HomePage() {
  return (
    <main className={styles.page}>
      <h1 className={styles.title}>Early Mind</h1>
      <Link to={paths.alphabet} className={styles.section}>
        <span className={styles.sectionImage} aria-hidden="true">
          А Б В
        </span>
        <span>Алфавит</span>
      </Link>
      <Link to={paths.parent} className={styles.parent}>
        Для родителя
      </Link>
    </main>
  );
}
