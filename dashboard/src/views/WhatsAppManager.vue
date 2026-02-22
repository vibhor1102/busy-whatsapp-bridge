<template>
  <div class="page-container">
    <h1>WhatsApp Manager</h1>
    <Card>
      <template #content>
        <p>WhatsApp management features coming soon... (Phase 3)</p>
        <Button label="Go to QR Code Page" icon="pi pi-qrcode" @click="openQRPage" />
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import Card from 'primevue/card'
import Button from 'primevue/button'

const openQRPage = () => {
  window.open('/baileys/qr', '_blank')
}
</script>

<style scoped>
.page-container {
  padding: 1.5rem;
}
</style>
