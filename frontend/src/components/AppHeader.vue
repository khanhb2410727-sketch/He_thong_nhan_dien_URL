<template>
  <header class="topbar">
    <RouterLink to="/" class="brand">
      <span class="brand-mark"><ShieldCheck :size="21" /></span>
      <span class="brand-copy"><strong>SafeLink<span>Scanner</span></strong><small>Scan any link for safety</small></span>
    </RouterLink>
    <nav class="nav-links">
      <RouterLink to="/">Home</RouterLink>
      <a href="#about" @click.prevent="scrollAbout">About</a>
      <a href="#api" @click.prevent="scrollApi">API</a>
      <a href="mailto: support@example.com">Contact</a>
    </nav>
  </header>
</template>
<script setup>
import { ShieldCheck } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
function scrollAbout() { document.getElementById('about')?.scrollIntoView({ behavior: 'smooth' }) }
function scrollApi() { document.getElementById('api')?.scrollIntoView({ behavior: 'smooth' }) }
</script>
