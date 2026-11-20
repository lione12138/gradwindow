import { makeElement, makeLink } from "./dom.js";
import { countryLabel, schoolLabels } from "./localization.js";

export function makeCell(label, ...children) {
  const cell = document.createElement("td");
  cell.dataset.label = label;
  cell.append(...children.filter(Boolean));
  return cell;
}

export function formatRank(rankDisplay) {
  return String(rankDisplay).startsWith("=") ? rankDisplay : `#${rankDisplay}`;
}

export function makeSchoolDisplay(record, language) {
  const school = document.createDocumentFragment();
  const labels = schoolLabels(record, language);
  const country = countryLabel(record.country, language);
  school.append(makeLink(labels.primary, record.applicationUrl, "school-link"));
  if (country) {
    school.append(
      makeElement("span", {
        className: "school-country-inline",
        text: `(${country})`,
      }),
    );
  }
  school.append(
    makeElement("span", {
      className: "school-meta",
      text: [labels.secondary, country].filter(Boolean).join(" · "),
    }),
  );
  return school;
}

export function makeSchoolGroupSummary(
  programmeCount,
  windowCount,
  expanded,
  t,
) {
  const summary = makeElement("div", { className: "school-group-summary" });
  const heading = makeElement("div", {
    className: "school-group-summary-heading",
  });
  heading.append(
    makeElement("span", {
      className: "school-group-kicker",
      text: t("schoolWindowGroup"),
    }),
    makeElement("span", {
      className: "school-group-state",
      text: t(expanded ? "schoolGroupExpanded" : "schoolGroupCollapsed"),
    }),
  );
  const programmes = `${programmeCount} ${t("programmes")}`;
  const counts = makeElement("div", { className: "school-group-counts" });
  counts.append(
    makeElement("strong", {
      className: "school-group-programme-count",
      text: programmes,
    }),
    makeElement("span", {
      className: "school-group-window-count",
      text: `${windowCount} ${t("windows")}`,
    }),
  );
  const label = expanded
    ? t("collapseSchoolWindows")
    : `${t("expandSchoolWindows")} ${programmes}`;
  const toggle = makeElement("button", {
    className: "window-group-toggle university-group-toggle",
    title: label,
  });
  toggle.type = "button";
  toggle.setAttribute("aria-expanded", String(expanded));
  const chevron = makeElement("span", {
    className: "school-group-chevron",
    text: "›",
  });
  chevron.setAttribute("aria-hidden", "true");
  toggle.append(makeElement("span", { text: label }), chevron);
  summary.append(heading, counts, toggle);
  return { summary, toggle };
}

export function createTrackerTable({
  status,
  heading,
  countLabel,
  columns,
  tableClass = "",
  sort,
  onSort,
}) {
  const section = makeElement("section", { className: "application-group" });
  section.dataset.status = status;
  const groupHeading = makeElement("div", { className: "group-heading" });
  const title = makeElement("h3");
  title.append(
    makeElement("span", { className: `status-indicator ${status}` }),
    document.createTextNode(heading.title),
  );
  groupHeading.append(
    title,
    makeElement("p", { text: `${heading.description} · ${countLabel}` }),
  );

  const wrapper = makeElement("div", { className: "table-wrap" });
  const table = makeElement("table", {
    className: `application-table ${tableClass}`.trim(),
  });
  const headRow = table.createTHead().insertRow();
  columns.forEach((column) => {
    const th = document.createElement("th");
    th.scope = "col";
    if (typeof column === "object" && column.sort) {
      const active = sort === column.sort;
      const button = makeElement("button", {
        className: `table-sort-button${active ? " active" : ""}`,
      });
      th.setAttribute("aria-sort", active ? "ascending" : "none");
      button.type = "button";
      button.dataset.sort = column.sort;
      button.append(
        makeElement("span", { text: column.label }),
        makeElement("span", {
          className: "sort-indicator",
          text: active ? "↑" : "↕",
        }),
      );
      button.addEventListener("click", () => onSort(column.sort));
      th.append(button);
    } else {
      th.textContent = typeof column === "object" ? column.label : column;
    }
    headRow.append(th);
  });
  const tbody = table.createTBody();
  wrapper.append(table);
  section.append(groupHeading, wrapper);
  return { section, tbody };
}
