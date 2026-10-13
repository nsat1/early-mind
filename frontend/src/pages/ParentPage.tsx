import { Link } from "react-router";
import { paths } from "../paths";
import styles from "./Page.module.css";

export function ParentPage() {
  return (
    <main className={styles.page}>
      <h1 className={styles.title}>Для родителя</h1>
      <Link to={paths.home}>На главную</Link>
    </main>
  );
}
