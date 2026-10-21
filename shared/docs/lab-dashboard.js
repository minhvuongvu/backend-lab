// Search / filter for hub/benchmarks.html. Classic deferred script; no-op on pages without the filter bar.
(() => {
  const bar = document.querySelector(".bench-filters");
  if (!bar) return;
  const search = bar.querySelector(".bench-search");
  const topic = bar.querySelector(".bench-topic");
  const multi = bar.querySelector(".bench-multi");
  const count = bar.querySelector(".bench-count");
  const groups = [...document.querySelectorAll(".bench-group")];
  const total = groups.reduce((n, g) => n + g.querySelectorAll("tbody tr").length, 0);

  function apply() {
    const q = (search.value || "").trim().toLowerCase();
    const t = topic.value;
    let shown = 0;
    for (const g of groups) {
      let visible = 0;
      for (const tr of g.querySelectorAll("tbody tr")) {
        const ok = (!q || tr.dataset.search.includes(q) || g.dataset.slug.includes(q)) && (!t || tr.dataset.topic === t);
        tr.hidden = !ok;
        if (ok) visible++;
      }
      g.hidden = visible === 0 || (multi.checked && g.dataset.multi !== "1");
      if (!g.hidden) shown += visible;
    }
    count.textContent = `${shown} / ${total} lần đo đang hiển thị`;
  }

  const params = new URLSearchParams(location.search);
  if (params.get("q")) search.value = params.get("q");
  if (params.get("topic")) topic.value = params.get("topic");
  search.addEventListener("input", apply);
  topic.addEventListener("change", apply);
  multi.addEventListener("change", apply);
  apply();
})();
