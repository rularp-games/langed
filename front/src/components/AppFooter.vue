<template>
  <footer class="footer">
    <div class="container footer__inner">
      <span>Langed — кабинетные ролевые игры</span>
      <RouterLink to="/roadmap">Планы развития</RouterLink>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  margin-top: var(--space-12);
  border-top: 1px solid var(--border);
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.footer__inner {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-2) var(--space-4);
  padding-block: var(--space-5);
}
.footer a {
  color: var(--text-muted);
}
.footer a:hover {
  color: var(--text);
}
</style>
