import { Link, NavLink, Outlet } from "react-router";
import { HomeIcon } from "../../components/HomeIcon";
import { paths } from "../../paths";
import styles from "./AlphabetLayout.module.css";

function tabClassName({ isActive }: { isActive: boolean }) {
  return isActive ? `${styles.tab} ${styles.activeTab}` : styles.tab;
}

export function AlphabetLayout() {
  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <Link to={paths.home} className={styles.home} aria-label="На главную">
          <HomeIcon />
        </Link>
      </header>
      <main className={styles.content}>
        <Outlet />
      </main>
      <nav className={styles.tabs} aria-label="Алфавит">
        <NavLink to={paths.letters} className={tabClassName}>
          <span className={styles.tabIcon} aria-hidden="true">
            Аа
          </span>
          <span>Буквы</span>
        </NavLink>
        <NavLink to={paths.tasks} className={tabClassName}>
          <span className={styles.tabIcon} aria-hidden="true">
            ?
          </span>
          <span>Задания</span>
        </NavLink>
      </nav>
    </div>
  );
}
