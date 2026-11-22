<template>
  <div class="app-shell">
    <AppHeader />
    <main class="main-container"><RouterView /></main>
    <footer class="site-footer"><span>© {{ new Date().getFullYear() }} SafeLink Scanner</span><span>Malicious URL Detection System</span></footer>
  </div>
</template>
<script setup>
import { RouterView } from 'vue-router'
import AppHeader from './components/AppHeader.vue'
</script>
