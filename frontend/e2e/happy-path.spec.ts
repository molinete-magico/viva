import { expect, test } from '@playwright/test'

const stamp = Date.now().toString(36)
const email = `e2e-${stamp}@viva.app`
const password = 'senha123'
const userName = `E2E ${stamp}`

test('fluxo completo: conta, personagem, feed, follow, DM, evento e mundo', async ({ page }) => {
  // 1. Criar conta
  await page.goto('/register')
  await page.getByLabel('E-mail').fill(email)
  await page.getByLabel('Senha (mínimo 6 caracteres)').fill(password)
  await page.getByRole('button', { name: 'Criar conta' }).click()
  await expect(page).toHaveURL(/\/onboarding/)

  // 2. Criar personagem → app leva ao perfil
  await page.getByPlaceholder('Como todo mundo te chama').fill(userName)
  await page.getByPlaceholder('Motorista de dia, garçom à noite…').fill('Guia de trilhas')
  await page.getByRole('button', { name: 'Começar a vida na cidade' }).click()
  await expect(page).toHaveURL(/\/profile\/\d+/)
  await page.getByRole('link', { name: 'Feed' }).click()
  await expect(page).toHaveURL(/\/feed/)

  // 3. Publicar um post
  const postText = `um post da rodada ${stamp}`
  await page.getByPlaceholder('O que está acontecendo na cidade?').fill(postText)
  await page.getByRole('button', { name: 'Publicar' }).click()
  await expect(page.getByText(postText)).toBeVisible()

  // 4. Explorar e acompanhar um morador (NPC)
  await page.getByRole('link', { name: 'Explorar' }).first().click()
  await expect(page).toHaveURL(/\/explore/)
  await expect(page.getByRole('heading', { name: 'Explorar a cidade' })).toBeVisible()
  const token = await page.evaluate(() => localStorage.getItem('viva_token'))
  const listing = await (
    await page.request.get('/api/characters', { headers: { Authorization: `Bearer ${token}` } })
  ).json()
  const npc = (listing.items ?? []).find((c) => c.is_npc)
  expect(npc, 'deve existir um NPC na cidade').toBeTruthy()
  await page.goto(`/profile/${npc.id}`)
  await expect(page).toHaveURL(/\/profile\/\d+/)
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await page.getByRole('button', { name: 'Seguir' }).click()
  await expect(page.getByRole('button', { name: /Seguindo/ })).toBeVisible()

  // 5. Conversar com o morador
  await page.getByRole('button', { name: 'Conversar' }).click()
  await expect(page).toHaveURL(/\/messages\/\d+/)
  const dmText = `oi, tudo bem? ${stamp}`
  await page.getByPlaceholder(/Escrever para/).fill(dmText)
  await page.getByRole('button', { name: 'Enviar' }).click()
  await expect(page.getByRole('paragraph').filter({ hasText: dmText })).toBeVisible()

  // 6. Criar um evento
  await page.getByRole('link', { name: 'Eventos' }).first().click()
  await expect(page).toHaveURL(/\/events/)
  await page.getByRole('button', { name: 'Criar' }).click()
  const eventTitle = `Rolê E2E ${stamp}`
  await page.getByPlaceholder('Título do evento').fill(eventTitle)
  await page.getByRole('combobox').selectOption({ index: 1 })
  await page.locator('input[type="datetime-local"]').fill('2030-01-01T20:00')
  await page.getByRole('button', { name: 'Marcar evento' }).click()
  await expect(page.getByText(eventTitle)).toBeVisible()

  // 7. Avançar o relógio do mundo (via Configurações)
  await page.getByRole('link', { name: 'Configurações' }).click()
  await page.getByRole('link', { name: 'Relógio da cidade' }).click()
  await expect(page).toHaveURL(/\/world/)
  await page.getByRole('button', { name: 'Pular para o próximo dia' }).click()
  await expect(page.getByRole('alert')).toBeVisible({ timeout: 30_000 })
})