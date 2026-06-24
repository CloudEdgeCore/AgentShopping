<template>
  <div class="flex h-screen flex-col overflow-hidden bg-[radial-gradient(circle_at_top_left,#ccfbf1_0,#f8fafc_34%,#fefce8_100%)]">
    <header class="shrink-0 border-b border-slate-200/80 bg-white/80 backdrop-blur">
      <div class="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <div class="flex items-center gap-3">
          <div class="flex h-11 w-11 items-center justify-center rounded-lg bg-slate-950 text-white shadow-panel">
            <ShoppingBag class="h-5 w-5" />
          </div>
          <div>
            <h1 class="text-xl font-semibold text-slate-950 sm:text-2xl">Commerce RAG Debug</h1>
            <p class="text-sm text-slate-600">多模态导购 Agent 调试工作台</p>
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <span :class="healthBadgeClass" class="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium">
            <span class="h-2 w-2 rounded-full bg-current"></span>
            {{ health?.status || "unknown" }}
          </span>
          <button class="btn-secondary" title="刷新健康检查" @click="() => refreshAll()">
            <RefreshCcw class="h-4 w-4" />
            刷新
          </button>
        </div>
      </div>
    </header>

    <main class="mx-auto grid min-h-0 w-full max-w-7xl flex-1 gap-4 overflow-hidden px-4 py-5 sm:px-6 lg:grid-cols-[280px_minmax(0,1fr)_340px] lg:px-8">
      <aside class="thin-scrollbar min-h-0 space-y-4 overflow-y-auto pr-1">
        <section class="panel p-4">
          <div class="mb-4 flex items-center justify-between">
            <h2 class="section-title">运行环境</h2>
            <button class="icon-btn" title="保存环境配置" @click="saveAuth">
              <Save class="h-4 w-4" />
            </button>
          </div>
          <div class="space-y-3">
            <label class="field-label">
              Backend
              <input v-model.trim="auth.baseUrl" class="field-input" placeholder="http://127.0.0.1:8000" />
            </label>
            <label class="field-label">
              User ID
              <input v-model.trim="auth.userId" class="field-input" placeholder="test-user-001" />
            </label>
            <label class="field-label">
              Roles
              <input v-model.trim="auth.roles" class="field-input" placeholder="user,ops" />
            </label>
            <label class="field-label">
              Bearer Token
              <input v-model.trim="auth.token" class="field-input" type="password" placeholder="可选" />
            </label>
            <label class="field-label">
              Ops Key
              <input v-model.trim="auth.opsApiKey" class="field-input" type="password" placeholder="可选" />
            </label>
          </div>
        </section>

        <section class="panel overflow-hidden">
          <div class="flex items-center justify-between border-b border-slate-200/80 p-4">
            <h2 class="section-title">会话</h2>
            <button class="icon-btn" title="新建会话" @click="createNewSession">
              <Plus class="h-4 w-4" />
            </button>
          </div>
          <div class="thin-scrollbar max-h-[360px] overflow-y-auto p-2">
            <button
              v-for="session in sessions"
              :key="session.id"
              :class="session.id === selectedSessionId ? 'border-teal-300 bg-teal-50 text-teal-950' : 'border-transparent bg-white text-slate-700 hover:bg-slate-50'"
              class="group mb-2 grid w-full grid-cols-[1fr_auto] items-center gap-2 rounded-lg border px-3 py-3 text-left transition"
              @click="selectSession(session.id)"
            >
              <span class="min-w-0">
                <span class="block truncate text-sm font-semibold">{{ session.title }}</span>
                <span class="block text-xs text-slate-500">{{ formatTime(session.updatedAt) }}</span>
              </span>
              <span class="flex items-center gap-1">
                <span class="text-xs text-slate-400">{{ shortId(session.id) }}</span>
                <button class="icon-btn-sm opacity-60 hover:opacity-100" title="删除会话" @click.stop="deleteExistingSession(session.id)">
                  <Trash2 class="h-3.5 w-3.5" />
                </button>
              </span>
            </button>
            <div v-if="!sessions.length" class="empty-state">
              <MessagesSquare class="h-5 w-5" />
              暂无会话
            </div>
          </div>
        </section>

        <section class="panel p-4">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="section-title">用户画像</h2>
            <button class="icon-btn" title="保存偏好" @click="savePreference">
              <SlidersHorizontal class="h-4 w-4" />
            </button>
          </div>
          <textarea v-model="preferenceText" class="field-textarea min-h-28" spellcheck="false"></textarea>
        </section>
      </aside>

      <section class="panel flex min-h-0 flex-col overflow-hidden">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200/80 px-4 py-3">
          <div>
            <h2 class="section-title">导购对话</h2>
            <p class="text-xs text-slate-500">Session {{ selectedSessionId ? shortId(selectedSessionId) : "自动创建" }}</p>
          </div>
          <div class="flex items-center gap-2">
            <button class="icon-btn" title="打开摄像头" @click="openCamera">
              <Camera class="h-4 w-4" />
            </button>
            <label class="icon-btn cursor-pointer" title="上传图片">
              <ImageUp class="h-4 w-4" />
              <input class="hidden" type="file" accept="image/png,image/jpeg,image/webp" @change="handleUploadChange" />
            </label>
            <button class="btn-secondary" title="清空当前页面消息" @click="clearLocalMessages">
              <Eraser class="h-4 w-4" />
              清屏
            </button>
          </div>
        </div>

        <div ref="messageScrollRef" class="thin-scrollbar flex-1 space-y-4 overflow-y-auto bg-white/55 p-4">
          <div v-if="isCameraOpen" class="rounded-lg border border-slate-200 bg-slate-950 p-3 shadow-sm">
            <video ref="cameraVideoRef" class="aspect-video w-full rounded-lg bg-black object-cover" autoplay playsinline muted></video>
            <canvas ref="cameraCanvasRef" class="hidden"></canvas>
            <div class="mt-3 flex flex-wrap items-center justify-between gap-2">
              <span class="text-sm font-medium text-slate-200">Camera</span>
              <div class="flex gap-2">
                <button class="btn-secondary" title="拍照并上传" @click="capturePhoto">
                  <Camera class="h-4 w-4" />
                  拍照
                </button>
                <button class="btn-secondary" title="关闭摄像头" @click="closeCamera">
                  <CameraOff class="h-4 w-4" />
                  关闭
                </button>
              </div>
            </div>
          </div>

          <div v-if="uploadPreviewUrl" class="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
            <img :src="uploadPreviewUrl" alt="uploaded preview" class="h-16 w-16 rounded-lg object-cover" />
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-semibold text-amber-950">{{ uploadResult?.upload_id }}</p>
              <p class="text-xs text-amber-700">图片将随下一条消息进入多模态检索</p>
            </div>
            <button class="icon-btn" title="移除图片" @click="clearUpload">
              <X class="h-4 w-4" />
            </button>
          </div>

          <div v-if="visionPanel" class="rounded-lg border border-teal-200 bg-teal-50 p-3">
            <div class="mb-2 flex items-start justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-teal-950">视觉主体候选</p>
                <p class="text-xs leading-5 text-teal-700">
                  {{ String(visionPanel.summary || "已完成图片理解") }}
                  <span v-if="visionPanel.confidence"> · 置信度 {{ percent(Number(visionPanel.confidence)) }}</span>
                </p>
              </div>
              <span v-if="visionPanel.needs_clarification" class="badge bg-amber-100 text-amber-700">需确认主体</span>
            </div>
            <div v-if="visionCandidates.length" class="flex flex-wrap gap-2">
              <button
                v-for="candidate in visionCandidates"
                :key="candidate.id || candidate.label"
                class="chip bg-white"
                title="按这个主体重新图搜"
                @click="searchVisionCandidate(candidate)"
              >
                <Search class="h-3.5 w-3.5" />
                {{ candidate.label }}
              </button>
            </div>
          </div>

          <div v-for="message in messages" :key="message.id" class="space-y-3">
            <div :class="message.role === 'user' ? 'ml-auto bg-slate-950 text-white' : 'mr-auto border border-slate-200 bg-white text-slate-800 shadow-sm'" class="max-w-[88%] rounded-lg px-4 py-3">
              <div class="mb-1 flex items-center gap-2 text-xs opacity-75">
                <User v-if="message.role === 'user'" class="h-3.5 w-3.5" />
                <Bot v-else class="h-3.5 w-3.5" />
                {{ message.role === "user" ? auth.userId : "Assistant" }}
              </div>
              <div class="prose-chat text-sm leading-6">{{ message.content || "..." }}</div>
            </div>

            <div v-if="message.productCards?.length" class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <article v-for="card in message.productCards" :key="productIdOf(card)" class="rounded-lg border border-slate-200 bg-white p-3 shadow-sm transition hover:-translate-y-0.5 hover:shadow-panel">
                <img
                  v-if="card.image_url"
                  :src="absoluteUrl(auth.baseUrl, card.image_url)"
                  :alt="card.title"
                  class="mb-3 aspect-[4/3] w-full rounded-lg bg-slate-100 object-cover"
                />
                <div class="mb-2 flex items-start justify-between gap-2">
                  <h3 class="line-clamp-2 text-sm font-semibold text-slate-950">{{ card.title }}</h3>
                  <span class="rounded-lg bg-rose-50 px-2 py-1 text-sm font-bold text-rose-700">{{ currency(card.price) }}</span>
                </div>
                <div class="mb-3 flex flex-wrap gap-2 text-xs text-slate-500">
                  <span class="badge">{{ card.category || "未分类" }}</span>
                  <span class="badge">{{ card.stock_status || `库存 ${card.stock ?? "--"}` }}</span>
                  <span class="badge">评分 {{ card.rating ?? "--" }}</span>
                </div>
                <ul v-if="card.reasons?.length" class="mb-3 space-y-1 text-xs leading-5 text-slate-600">
                  <li v-for="reason in card.reasons.slice(0, 3)" :key="reason" class="flex gap-2">
                    <CheckCircle2 class="mt-0.5 h-3.5 w-3.5 flex-none text-teal-600" />
                    <span>{{ reason }}</span>
                  </li>
                </ul>
                <div class="grid grid-cols-6 gap-2">
                  <button class="action-btn col-span-2" title="加入购物车" @click="addToCart(card)">
                    <ShoppingCart class="h-4 w-4" />
                    加购
                  </button>
                  <button class="action-btn" title="立即结算" @click="buyNow(card)">
                    <CreditCard class="h-4 w-4" />
                  </button>
                  <button class="action-btn" title="查看商品详情" @click="inspectProduct(card)">
                    <Info class="h-4 w-4" />
                  </button>
                  <button class="action-btn" title="收藏商品" @click="toggleCollection('favorite', productIdOf(card))">
                    <Heart class="h-4 w-4" />
                  </button>
                  <button class="action-btn" title="加入对比" @click="toggleCollection('compare', productIdOf(card))">
                    <GitCompareArrows class="h-4 w-4" />
                  </button>
                </div>
              </article>
            </div>

            <div v-if="message.role === 'assistant' && message.feedbackEnabled" class="flex gap-2">
              <button class="icon-btn" title="推荐有帮助" @click="sendFeedback(message.id, 1)">
                <ThumbsUp class="h-4 w-4" />
              </button>
              <button class="icon-btn" title="推荐需改进" @click="sendFeedback(message.id, -1, 'weak_reason')">
                <ThumbsDown class="h-4 w-4" />
              </button>
            </div>
          </div>

          <div v-if="!messages.length" class="empty-state min-h-[420px] justify-center">
            <Sparkles class="h-8 w-8" />
            <span class="text-base font-semibold">输入购物需求开始调试</span>
            <div class="mt-4 flex flex-wrap justify-center gap-2">
              <button v-for="sample in samples" :key="sample" class="chip" @click="composer = sample">
                {{ sample }}
              </button>
            </div>
          </div>
        </div>

        <div class="border-t border-slate-200/80 bg-white p-4">
          <div v-if="streamStatus.length" class="mb-3 flex flex-wrap gap-2">
            <span v-for="status in streamStatus.slice(-4)" :key="status.stage + status.label" class="badge bg-teal-50 text-teal-700">
              {{ status.label }}
            </span>
          </div>
          <form class="flex flex-col gap-3 sm:flex-row" @submit.prevent="sendMessage">
            <textarea
              v-model="composer"
              class="field-textarea min-h-20 flex-1"
              placeholder="例如：预算 500 内，通勤用降噪耳机，最好现货"
              @keydown.ctrl.enter.prevent="sendMessage"
            ></textarea>
            <div class="grid grid-cols-2 gap-2 sm:w-48">
              <button
                :disabled="isTranscribing"
                :class="isRecording ? 'border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100' : ''"
                class="btn-secondary"
                title="录音转文字"
                type="button"
                @click="toggleRecording"
              >
                <Loader2 v-if="isTranscribing" class="h-4 w-4 animate-spin" />
                <Square v-else-if="isRecording" class="h-4 w-4 fill-current" />
                <Mic v-else class="h-4 w-4" />
                {{ isRecording ? recordingSecondsText : "语音" }}
              </button>
              <button :disabled="isSending || !composer.trim()" class="btn-primary" type="submit">
                <Loader2 v-if="isSending" class="h-4 w-4 animate-spin" />
                <Send v-else class="h-4 w-4" />
                发送
              </button>
            </div>
          </form>
        </div>
      </section>

      <aside class="thin-scrollbar min-h-0 space-y-4 overflow-y-auto pr-1">
        <section class="panel overflow-hidden">
          <div class="flex items-center justify-between border-b border-slate-200/80 p-4">
            <h2 class="section-title">购物车</h2>
            <button class="icon-btn" title="刷新购物车" @click="loadCart">
              <RefreshCcw class="h-4 w-4" />
            </button>
          </div>
          <div class="space-y-3 p-4">
            <div v-for="item in cart.items" :key="item.cart_item_id" class="rounded-lg border border-slate-200 bg-white p-3">
              <div class="flex gap-3">
                <img v-if="item.image_url" :src="absoluteUrl(auth.baseUrl, item.image_url)" :alt="item.title" class="h-14 w-14 rounded-lg object-cover" />
                <div class="min-w-0 flex-1">
                  <p class="truncate text-sm font-semibold text-slate-950">{{ item.title }}</p>
                  <p class="text-xs text-slate-500">{{ currency(item.unit_price) }} x {{ item.quantity }}</p>
                </div>
              </div>
              <div class="mt-3 flex items-center justify-between">
                <div class="flex items-center gap-1">
                  <button class="icon-btn-sm" title="减少数量" @click="updateCartQuantity(item, item.quantity - 1)">
                    <Minus class="h-3.5 w-3.5" />
                  </button>
                  <span class="w-7 text-center text-sm font-semibold">{{ item.quantity }}</span>
                  <button class="icon-btn-sm" title="增加数量" @click="updateCartQuantity(item, item.quantity + 1)">
                    <Plus class="h-3.5 w-3.5" />
                  </button>
                </div>
                <button class="icon-btn-sm" title="移出购物车" @click="removeCartItem(item.cart_item_id)">
                  <Trash2 class="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
            <div v-if="!cart.items.length" class="empty-state py-8">
              <ShoppingCart class="h-5 w-5" />
              购物车为空
            </div>
            <div class="rounded-lg bg-slate-950 p-4 text-white">
              <div class="flex items-center justify-between text-sm">
                <span>合计</span>
                <strong class="text-xl">{{ currency(cart.subtotal_amount) }}</strong>
              </div>
              <button :disabled="!cart.items.length" class="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-slate-950 transition hover:bg-teal-50 disabled:cursor-not-allowed disabled:opacity-50" @click="previewCartCheckout">
                <CreditCard class="h-4 w-4" />
                预览结算
              </button>
            </div>
          </div>
        </section>

        <section class="panel overflow-hidden">
          <div class="grid grid-cols-3 border-b border-slate-200/80 text-xs font-semibold">
            <button
              v-for="tab in collectionTabs"
              :key="tab.id"
              :class="collectionTab === tab.id ? 'bg-teal-700 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'"
              class="px-2 py-3 transition"
              @click="setCollectionTab(tab.id)"
            >
              {{ tab.label }}
            </button>
          </div>
          <div class="thin-scrollbar max-h-72 space-y-3 overflow-y-auto p-4">
            <div v-for="item in activeCollectionItems" :key="item.id" class="flex gap-3 rounded-lg border border-slate-200 bg-white p-3">
              <img v-if="item.product.image_url" :src="absoluteUrl(auth.baseUrl, item.product.image_url)" :alt="item.product.title" class="h-12 w-12 rounded-lg object-cover" />
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-semibold text-slate-950">{{ item.product.title }}</p>
                <p class="text-xs text-slate-500">{{ currency(item.product.price) }} · {{ item.product.category }}</p>
              </div>
              <button class="icon-btn-sm" title="查看详情" @click="inspectProduct(item.product)">
                <Info class="h-3.5 w-3.5" />
              </button>
            </div>
            <div v-if="!activeCollectionItems.length" class="empty-state py-6">
              <History class="h-5 w-5" />
              暂无{{ activeCollectionLabel }}
            </div>
          </div>
        </section>

        <section v-if="checkoutPreview" class="panel p-4">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="section-title">结算快照</h2>
            <span class="badge bg-amber-50 text-amber-700">{{ checkoutPreview.status }}</span>
          </div>
          <div class="space-y-2 text-sm text-slate-600">
            <div class="flex justify-between"><span>商品</span><span>{{ currency(checkoutPreview.subtotal_amount) }}</span></div>
            <div class="flex justify-between"><span>运费</span><span>{{ currency(checkoutPreview.shipping_fee) }}</span></div>
            <div class="flex justify-between font-semibold text-slate-950"><span>应付</span><span>{{ currency(checkoutPreview.payable_amount) }}</span></div>
          </div>
          <button class="btn-primary mt-4 w-full" @click="confirmCheckout">
            <ShieldCheck class="h-4 w-4" />
            确认下单
          </button>
        </section>

        <section v-if="productPanel" class="panel overflow-hidden">
          <div class="flex items-start justify-between gap-3 border-b border-slate-200/80 p-4">
            <div class="min-w-0">
              <h2 class="truncate text-sm font-semibold text-slate-950">{{ productPanel.title }}</h2>
              <p class="text-xs text-slate-500">{{ productPanel.category }} · {{ currency(productPanel.price) }}</p>
            </div>
            <div class="flex gap-2">
              <button class="icon-btn-sm" title="收藏" @click="toggleCollection('favorite', productPanel.product_id)">
                <Heart class="h-3.5 w-3.5" />
              </button>
              <button class="icon-btn-sm" title="对比" @click="toggleCollection('compare', productPanel.product_id)">
                <GitCompareArrows class="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
          <div class="thin-scrollbar max-h-[520px] space-y-4 overflow-y-auto p-4">
            <div class="grid grid-cols-[84px_minmax(0,1fr)] gap-3">
              <img v-if="productPanel.image_url" :src="absoluteUrl(auth.baseUrl, productPanel.image_url)" :alt="productPanel.title" class="h-20 w-20 rounded-lg object-cover" />
              <div class="space-y-2 text-xs text-slate-600">
                <div class="flex flex-wrap gap-2">
                  <span class="badge">评分 {{ productPanel.rating ?? "--" }}</span>
                  <span class="badge">库存 {{ productPanel.stock ?? "--" }}</span>
                  <span class="badge">销量 {{ productPanel.sales ?? "--" }}</span>
                </div>
                <p class="line-clamp-3 leading-5">{{ productPanel.description }}</p>
              </div>
            </div>

            <div v-if="productPanel.reviewSummary" class="space-y-3">
              <div class="flex items-center justify-between">
                <h3 class="text-xs font-semibold uppercase tracking-normal text-slate-500">评价摘要</h3>
                <span class="text-xs text-slate-500">{{ productPanel.reviewSummary.total_reviews }} 条 · {{ productPanel.reviewSummary.source }}</span>
              </div>
              <div class="grid grid-cols-5 gap-1">
                <div v-for="score in [5, 4, 3, 2, 1]" :key="score" class="rounded-lg bg-slate-100 px-2 py-1 text-center text-xs text-slate-600">
                  {{ score }}星 {{ productPanel.reviewSummary.rating_histogram[String(score)] || 0 }}
                </div>
              </div>
              <div class="flex flex-wrap gap-2">
                <span v-for="item in productPanel.reviewSummary.positive_tags.slice(0, 4)" :key="item.tag" class="badge bg-teal-50 text-teal-700">
                  {{ item.tag }} {{ item.count }}
                </span>
                <span v-for="item in productPanel.reviewSummary.risk_tags.slice(0, 3)" :key="item.tag" class="badge bg-amber-50 text-amber-700">
                  {{ item.tag }} {{ item.count }}
                </span>
              </div>
              <div v-if="productPanel.reviewSummary.dimensions.length" class="space-y-2">
                <div v-for="dimension in productPanel.reviewSummary.dimensions.slice(0, 4)" :key="dimension.name" class="rounded-lg border border-slate-200 bg-white p-2">
                  <div class="flex items-center justify-between text-xs">
                    <span class="font-semibold text-slate-700">{{ dimension.name }}</span>
                    <span :class="dimension.sentiment === 'negative' ? 'text-amber-700' : 'text-teal-700'">{{ dimension.sentiment }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="productPanel.questions" class="space-y-3">
              <div class="flex items-center justify-between">
                <h3 class="text-xs font-semibold uppercase tracking-normal text-slate-500">商品问答</h3>
                <span class="text-xs text-slate-500">待回答 {{ productPanel.questions.pending_count }}</span>
              </div>
              <div v-for="qa in productPanel.questions.questions.slice(0, 3)" :key="qa.id" class="rounded-lg border border-slate-200 bg-white p-3 text-xs leading-5">
                <p class="font-semibold text-slate-800">问：{{ qa.question }}</p>
                <p class="mt-1 text-slate-600">答：{{ qa.answer || "等待运营回答" }}</p>
              </div>
              <form class="flex gap-2" @submit.prevent="submitProductQuestion">
                <input v-model.trim="questionDraft" class="field-input mt-0" placeholder="问商品规格、适用场景或售后" />
                <button class="icon-btn" title="提交问题" type="submit">
                  <MessageCircleQuestion class="h-4 w-4" />
                </button>
              </form>
            </div>
          </div>
        </section>

        <section class="panel overflow-hidden">
          <div class="grid grid-cols-4 border-b border-slate-200/80 text-sm font-medium">
            <button v-for="tab in tabs" :key="tab.id" :class="activeTab === tab.id ? 'bg-slate-950 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'" class="px-3 py-3 transition" @click="setActiveTab(tab.id)">
              {{ tab.label }}
            </button>
          </div>
          <div class="thin-scrollbar max-h-[560px] overflow-y-auto p-4">
            <div v-if="activeTab === 'trace'" class="space-y-3">
              <pre class="json-box">{{ stringifyPretty(trace) }}</pre>
            </div>
            <div v-else-if="activeTab === 'health'" class="space-y-3">
              <pre class="json-box">{{ stringifyPretty(health) }}</pre>
              <pre class="json-box">{{ stringifyPretty(voiceCapabilities) }}</pre>
            </div>
            <div v-else-if="activeTab === 'ops'" class="space-y-4">
              <div v-if="dashboard?.kpis" class="grid grid-cols-2 gap-2">
                <div v-for="item in dashboardKpis" :key="item.label" class="rounded-lg border border-slate-200 bg-white p-3">
                  <p class="text-xs text-slate-500">{{ item.label }}</p>
                  <p class="mt-1 text-lg font-semibold text-slate-950">{{ item.value }}</p>
                </div>
              </div>
              <div v-if="dashboard?.funnel?.length" class="space-y-2">
                <h3 class="text-xs font-semibold uppercase tracking-normal text-slate-500">转化漏斗</h3>
                <div v-for="stage in dashboard.funnel" :key="stage.stage" class="grid grid-cols-[88px_1fr_36px] items-center gap-2 text-xs">
                  <span class="truncate text-slate-600">{{ stage.stage }}</span>
                  <div class="h-2 rounded-full bg-slate-100">
                    <div class="h-2 rounded-full bg-teal-600" :style="{ width: `${funnelWidth(stage.count)}%` }"></div>
                  </div>
                  <span class="text-right font-semibold text-slate-700">{{ stage.count }}</span>
                </div>
              </div>
              <div v-if="topNoResultQueries.length" class="space-y-2">
                <h3 class="text-xs font-semibold uppercase tracking-normal text-slate-500">无结果查询</h3>
                <div v-for="item in topNoResultQueries" :key="item.name" class="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-xs">
                  <span class="truncate text-slate-700">{{ item.name }}</span>
                  <span class="font-semibold text-slate-900">{{ item.count }}</span>
                </div>
              </div>
              <pre class="json-box">{{ stringifyPretty(dashboard) }}</pre>
            </div>
            <div v-else class="space-y-3">
              <pre class="json-box">{{ stringifyPretty(rawEvents.slice(-20)) }}</pre>
              <pre v-if="selectedProduct" class="json-box">{{ stringifyPretty(selectedProduct) }}</pre>
            </div>
          </div>
        </section>
      </aside>
    </main>

    <div v-if="toast" class="fixed bottom-5 left-1/2 z-50 w-[min(560px,calc(100vw-2rem))] -translate-x-1/2 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 shadow-panel">
      {{ toast }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import {
  Bot,
  Camera,
  CameraOff,
  CheckCircle2,
  CreditCard,
  Eraser,
  GitCompareArrows,
  Heart,
  History,
  ImageUp,
  Info,
  Loader2,
  MessageCircleQuestion,
  MessagesSquare,
  Mic,
  Minus,
  Plus,
  RefreshCcw,
  Save,
  Search,
  Send,
  ShieldCheck,
  ShoppingBag,
  ShoppingCart,
  SlidersHorizontal,
  Sparkles,
  Square,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  User,
  X,
} from "lucide-vue-next";
import { ApiClient } from "./api";
import type {
  AuthConfig,
  CartItem,
  CartState,
  ChatMessage,
  CheckoutPreview,
  HealthPayload,
  OpsDashboard,
  OpsMetrics,
  ProductCardData,
  ProductQuestions,
  ProductReviewSummary,
  SessionSummary,
  StreamStatus,
  UploadResult,
  UserProductCollectionItem,
  VisionObjectCandidate,
  VoiceCapabilities,
} from "./types";
import {
  absoluteUrl,
  asErrorMessage,
  currency,
  defaultAuth,
  formatTime,
  persistAuth,
  productIdOf,
  shortId,
  stringifyPretty,
} from "./utils";

const auth = reactive<AuthConfig>({ ...defaultAuth });
const sessions = ref<SessionSummary[]>([]);
const selectedSessionId = ref("");
const messages = ref<ChatMessage[]>([]);
const composer = ref("");
const isSending = ref(false);
const uploadResult = ref<UploadResult | null>(null);
const health = ref<HealthPayload | null>(null);
const metrics = ref<OpsMetrics | null>(null);
const dashboard = ref<OpsDashboard | null>(null);
const voiceCapabilities = ref<VoiceCapabilities | null>(null);
const trace = ref<unknown[]>([]);
const rawEvents = ref<Array<{ event: string; payload: unknown; at: string }>>([]);
const streamStatus = ref<StreamStatus[]>([]);
const selectedProduct = ref<unknown>(null);
const productPanel = ref<ProductPanel | null>(null);
const questionDraft = ref("");
const visionPanel = ref<Record<string, unknown> | null>(null);
const lastVisionUploadId = ref("");
const preferenceText = ref('{"budget_max": 800, "style": "实用优先", "avoid": []}');
const checkoutPreview = ref<CheckoutPreview | null>(null);
const toast = ref("");
const activeTab = ref<"trace" | "health" | "ops" | "raw">("trace");
const cart = reactive<CartState>({ items: [], total_quantity: 0, subtotal_amount: 0 });
const collectionTab = ref<CollectionListType>("favorite");
const lazyLoaded = reactive({
  collections: false,
  ops: false,
  voice: false,
  deepHealth: false,
});
const collections = reactive<Record<CollectionListType, UserProductCollectionItem[]>>({
  favorite: [],
  compare: [],
  recent: [],
});
const cameraVideoRef = ref<HTMLVideoElement | null>(null);
const cameraCanvasRef = ref<HTMLCanvasElement | null>(null);
const messageScrollRef = ref<HTMLDivElement | null>(null);
const cameraStream = ref<MediaStream | null>(null);
const isCameraOpen = ref(false);
const mediaRecorder = ref<MediaRecorder | null>(null);
const audioChunks = ref<Blob[]>([]);
const isRecording = ref(false);
const isTranscribing = ref(false);
const recordingSeconds = ref(0);
let recordingTimer: number | undefined;

const samples = [
  "预算 500 内，通勤用降噪耳机，最好续航久一点",
  "找一款适合油皮的夏季防晒，别太闷",
  "我想买一双适合日常慢跑的鞋，轻一点",
];

const tabs = [
  { id: "trace", label: "Trace" },
  { id: "health", label: "Health" },
  { id: "ops", label: "Ops" },
  { id: "raw", label: "Raw" },
] as const;

const collectionTabs = [
  { id: "favorite", label: "收藏" },
  { id: "compare", label: "对比" },
  { id: "recent", label: "最近" },
] as const;

type CollectionListType = "favorite" | "compare" | "recent";
interface ProductPanel {
  product_id: string;
  title: string;
  category?: string;
  price?: number;
  rating?: number;
  sales?: number;
  stock?: number;
  image_url?: string;
  description?: string;
  reviewSummary?: ProductReviewSummary;
  questions?: ProductQuestions;
  detail?: Record<string, unknown>;
  intelligence?: Record<string, unknown>;
}

const api = computed(() => new ApiClient(auth));
const uploadPreviewUrl = computed(() => absoluteUrl(auth.baseUrl, uploadResult.value?.preview_url));
const recordingSecondsText = computed(() => `${Math.max(recordingSeconds.value, 1)}s`);
const healthBadgeClass = computed(() => {
  const status = String(health.value?.status || "").toLowerCase();
  if (status === "ok") return "bg-teal-50 text-teal-700";
  if (status === "warn") return "bg-amber-50 text-amber-700";
  if (status === "error") return "bg-rose-50 text-rose-700";
  return "bg-slate-100 text-slate-600";
});
const activeCollectionItems = computed(() => collections[collectionTab.value] || []);
const activeCollectionLabel = computed(() => collectionTabs.find((tab) => tab.id === collectionTab.value)?.label || "");
const visionCandidates = computed<VisionObjectCandidate[]>(() => {
  const raw = visionPanel.value?.object_candidates;
  return Array.isArray(raw) ? (raw as VisionObjectCandidate[]) : [];
});
const dashboardKpis = computed(() => {
  const kpis = dashboard.value?.kpis || {};
  return [
    { label: "会话", value: numberMetric(kpis.sessions) },
    { label: "无结果率", value: percent(Number(kpis.no_result_rate || 0)) },
    { label: "转化代理", value: percent(Number(kpis.conversion_proxy || 0)) },
    { label: "负反馈率", value: percent(Number(kpis.negative_feedback_rate || 0)) },
    { label: "平均延迟", value: `${numberMetric(kpis.avg_latency_ms)}ms` },
    { label: "LLM 错误", value: numberMetric(kpis.llm_error_count) },
  ];
});
const topNoResultQueries = computed<Array<{ name: string; count: number }>>(() => {
  const retrieval = dashboard.value?.retrieval;
  const rows = retrieval && Array.isArray(retrieval.top_no_result_queries) ? retrieval.top_no_result_queries : [];
  return rows as Array<{ name: string; count: number }>;
});

onMounted(() => {
  refreshInitial();
});

onBeforeUnmount(() => {
  closeCamera();
  stopRecordingTimer();
  if (mediaRecorder.value && mediaRecorder.value.state !== "inactive") {
    mediaRecorder.value.stop();
  }
});

async function refreshInitial() {
  await Promise.allSettled([
    loadHealth(false),
    loadSessions(),
    loadCart(),
    loadProfile(),
  ]);
  window.setTimeout(() => {
    void loadCollectionsOnce();
  }, 600);
}

async function refreshAll(full = false) {
  if (!full) {
    await refreshInitial();
    return;
  }
  await Promise.allSettled([
    loadHealth(true),
    loadSessions(),
    loadCart(),
    loadCollections(true),
    loadProfile(),
    loadMetrics(),
    loadDashboard(),
    loadVoiceCapabilities(),
  ]);
}

function saveAuth() {
  persistAuth(auth);
  notify("环境配置已保存");
  refreshAll(true);
}

async function loadHealth(deep = false) {
  try {
    health.value = await api.value.health(deep);
    if (deep) lazyLoaded.deepHealth = true;
  } catch (error) {
    health.value = { status: "error", detail: asErrorMessage(error) };
  }
}

async function loadMetrics() {
  try {
    metrics.value = await api.value.opsMetrics();
    lazyLoaded.ops = true;
  } catch (error) {
    metrics.value = { retrieval: { error: asErrorMessage(error) } };
  }
}

async function loadDashboard() {
  try {
    dashboard.value = await api.value.opsDashboard();
    lazyLoaded.ops = true;
  } catch (error) {
    dashboard.value = { kpis: { error: 1 }, retrieval: { error: asErrorMessage(error) } };
  }
}

async function loadVoiceCapabilities() {
  try {
    voiceCapabilities.value = await api.value.voiceCapabilities();
    lazyLoaded.voice = true;
    rawEvents.value.push({ event: "voice_capabilities", payload: voiceCapabilities.value, at: new Date().toISOString() });
  } catch (error) {
    voiceCapabilities.value = { asr: { configured: false, provider: "unknown", mode: asErrorMessage(error) } };
  }
}

async function loadSessions() {
  try {
    sessions.value = await api.value.sessions();
    if (!selectedSessionId.value && sessions.value[0]) {
      await selectSession(sessions.value[0].id);
    }
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

async function createNewSession() {
  try {
    const session = await api.value.createSession("导购会话");
    sessions.value = [session, ...sessions.value];
    await selectSession(session.id);
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

async function selectSession(sessionId: string) {
  selectedSessionId.value = sessionId;
  try {
    const history = (await api.value.messages(sessionId)) as Array<Record<string, unknown>>;
    messages.value = history.map((item) => ({
      id: String(item.id),
      role: item.role === "user" ? "user" : "assistant",
      content: String(item.content || ""),
      createdAt: String(item.createdAt || ""),
      productCards: Array.isArray(item.productCards) ? (item.productCards as ProductCardData[]) : [],
    }));
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

async function deleteExistingSession(sessionId: string) {
  try {
    await api.value.deleteSession(sessionId);
    sessions.value = sessions.value.filter((item) => item.id !== sessionId);
    if (selectedSessionId.value === sessionId) {
      selectedSessionId.value = "";
      messages.value = [];
      if (sessions.value[0]) await selectSession(sessions.value[0].id);
    }
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

function createMessageTypewriter(message: ChatMessage) {
  let pending = "";
  let timer: number | undefined;
  let drainResolvers: Array<() => void> = [];

  function resolveDrains() {
    const resolvers = drainResolvers;
    drainResolvers = [];
    resolvers.forEach((resolve) => resolve());
  }

  function stopTimer() {
    if (timer !== undefined) {
      window.clearTimeout(timer);
      timer = undefined;
    }
  }

  function schedule() {
    if (timer === undefined) timer = window.setTimeout(pump, 22);
  }

  function pump() {
    timer = undefined;
    if (!pending) {
      resolveDrains();
      return;
    }
    const take = nextTypewriterTake(pending);
    message.content += pending.slice(0, take);
    pending = pending.slice(take);
    scrollMessagesToBottom();
    if (pending) schedule();
    else resolveDrains();
  }

  return {
    push(text: string) {
      if (!text) return;
      pending += text;
      schedule();
    },
    replaceWithFinal(content: string) {
      if (content.startsWith(message.content)) {
        pending = content.slice(message.content.length);
      } else {
        message.content = "";
        pending = content;
      }
      if (pending) schedule();
      else resolveDrains();
    },
    reset() {
      stopTimer();
      pending = "";
      resolveDrains();
    },
    stop() {
      stopTimer();
      pending = "";
      resolveDrains();
    },
    drain() {
      if (!pending && timer === undefined) return Promise.resolve();
      return new Promise<void>((resolve) => {
        drainResolvers.push(resolve);
        schedule();
      });
    },
  };
}

function nextTypewriterTake(text: string) {
  if (text.startsWith("\n")) return 1;
  const first = text.codePointAt(0) || 0;
  return Math.min(text.length, first < 128 ? 4 : 2);
}

async function sendMessage() {
  const content = composer.value.trim();
  if (!content || isSending.value) return;
  isSending.value = true;
  composer.value = "";
  streamStatus.value = [];
  trace.value = [];

  const userMessage: ChatMessage = {
    id: `local-user-${Date.now()}`,
    role: "user",
    content,
  };
  const assistantMessage: ChatMessage = {
    id: `local-assistant-${Date.now()}`,
    role: "assistant",
    content: "",
    productCards: [],
  };
  messages.value.push(userMessage, assistantMessage);
  scrollMessagesToBottom();
  const typewriter = createMessageTypewriter(assistantMessage);
  const activeUploadId = uploadResult.value?.upload_id || "";
  if (activeUploadId) lastVisionUploadId.value = activeUploadId;

  try {
    await api.value.streamChat(
      {
        message: content,
        session_id: selectedSessionId.value || null,
        upload_id: activeUploadId || null,
        memory: parsePreference(),
      },
      {
        onStatus(payload) {
          streamStatus.value.push(payload);
          if (payload.session_id) selectedSessionId.value = payload.session_id;
        },
        onMessageStart(payload) {
          typewriter.reset();
          assistantMessage.id = String(payload.message_id || assistantMessage.id);
          assistantMessage.content = "";
          assistantMessage.feedbackEnabled = Boolean(payload.feedback_enabled);
          if (Array.isArray(payload.feedback_reasons)) assistantMessage.feedbackReasons = payload.feedback_reasons as never;
          if (payload.session_id) selectedSessionId.value = String(payload.session_id);
        },
        onMessageDelta(payload) {
          if (payload.message_id) assistantMessage.id = String(payload.message_id);
          typewriter.push(String(payload.delta || ""));
          if (payload.session_id) selectedSessionId.value = String(payload.session_id);
        },
        onMessage(payload) {
          assistantMessage.id = String(payload.message_id || assistantMessage.id);
          typewriter.replaceWithFinal(String(payload.content || ""));
          assistantMessage.feedbackEnabled = Boolean(payload.feedback_enabled);
          if (Array.isArray(payload.feedback_reasons)) assistantMessage.feedbackReasons = payload.feedback_reasons as never;
          if (payload.session_id) selectedSessionId.value = String(payload.session_id);
          if (payload.cart_state && typeof payload.cart_state === "object") applyCart(payload.cart_state as CartState);
        },
        onTrace(payload) {
          trace.value = payload;
        },
        onProducts(payload) {
          assistantMessage.productCards = payload;
        },
        onCart(payload) {
          applyCart(payload);
        },
        onVision(payload) {
          visionPanel.value = payload;
          selectedProduct.value = { vision_analysis: payload };
        },
        onComparison(payload) {
          selectedProduct.value = { comparison: payload };
        },
        onError(message) {
          typewriter.stop();
          assistantMessage.content = message;
          notify(message);
        },
        onRaw(event, payload) {
          rawEvents.value.push({ event, payload, at: new Date().toISOString() });
        },
      },
    );
    await typewriter.drain();
    uploadResult.value = null;
    await Promise.allSettled([loadSessions(), loadCart()]);
    void refreshSecondaryAfterTurn();
  } catch (error) {
    typewriter.stop();
    assistantMessage.content = asErrorMessage(error);
    notify(asErrorMessage(error));
  } finally {
    isSending.value = false;
  }
}

async function handleUploadChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  try {
    uploadResult.value = await api.value.uploadImage(file);
    notify("图片已上传");
  } catch (error) {
    notify(asErrorMessage(error));
  } finally {
    input.value = "";
  }
}

async function openCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    notify("当前浏览器不支持摄像头调用");
    return;
  }
  try {
    closeCamera();
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    });
    cameraStream.value = stream;
    isCameraOpen.value = true;
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    if (cameraVideoRef.value) {
      cameraVideoRef.value.srcObject = stream;
      await cameraVideoRef.value.play();
    }
  } catch (error) {
    notify(`摄像头打开失败：${asErrorMessage(error)}`);
  }
}

function closeCamera() {
  cameraStream.value?.getTracks().forEach((track) => track.stop());
  cameraStream.value = null;
  isCameraOpen.value = false;
  if (cameraVideoRef.value) cameraVideoRef.value.srcObject = null;
}

async function capturePhoto() {
  const video = cameraVideoRef.value;
  const canvas = cameraCanvasRef.value;
  if (!video || !canvas || video.readyState < 2) {
    notify("摄像头画面还没有准备好");
    return;
  }
  canvas.width = video.videoWidth || 1280;
  canvas.height = video.videoHeight || 720;
  const context = canvas.getContext("2d");
  if (!context) {
    notify("无法读取摄像头画面");
    return;
  }
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.9));
  if (!blob) {
    notify("拍照失败");
    return;
  }
  try {
    const file = new File([blob], `camera-${Date.now()}.jpg`, { type: "image/jpeg" });
    uploadResult.value = await api.value.uploadImage(file);
    closeCamera();
    notify("照片已上传");
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

function clearUpload() {
  uploadResult.value = null;
}

function clearLocalMessages() {
  messages.value = [];
  trace.value = [];
  rawEvents.value = [];
  streamStatus.value = [];
}

async function toggleRecording() {
  if (isRecording.value) {
    stopRecording();
  } else {
    await startRecording();
  }
}

async function startRecording() {
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    notify("当前浏览器不支持录音");
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks.value = [];
    const recorder = new MediaRecorder(stream, { mimeType: preferredAudioMimeType() });
    mediaRecorder.value = recorder;
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) audioChunks.value.push(event.data);
    };
    recorder.onstop = () => {
      stream.getTracks().forEach((track) => track.stop());
      handleRecordedAudio();
    };
    recorder.start();
    isRecording.value = true;
    recordingSeconds.value = 0;
    recordingTimer = window.setInterval(() => {
      recordingSeconds.value += 1;
    }, 1000);
  } catch (error) {
    notify(`录音打开失败：${asErrorMessage(error)}`);
  }
}

function stopRecording() {
  stopRecordingTimer();
  isRecording.value = false;
  if (mediaRecorder.value && mediaRecorder.value.state !== "inactive") {
    mediaRecorder.value.stop();
  }
}

async function handleRecordedAudio() {
  if (!audioChunks.value.length) return;
  isTranscribing.value = true;
  const type = audioChunks.value[0]?.type || preferredAudioMimeType();
  const blob = new Blob(audioChunks.value, { type });
  const file = new File([blob], `voice-${Date.now()}.${audioExtension(type)}`, { type });
  try {
    const result = await api.value.transcribeAudio(file);
    rawEvents.value.push({ event: "asr", payload: result, at: new Date().toISOString() });
    if (result.text) {
      composer.value = composer.value ? `${composer.value}\n${result.text}` : result.text;
      notify("语音已转成文字");
    } else {
      notify("没有识别到文字");
    }
  } catch (error) {
    notify(asErrorMessage(error));
  } finally {
    isTranscribing.value = false;
    audioChunks.value = [];
    mediaRecorder.value = null;
  }
}

function stopRecordingTimer() {
  if (recordingTimer !== undefined) {
    window.clearInterval(recordingTimer);
    recordingTimer = undefined;
  }
}

function preferredAudioMimeType(): string {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "audio/webm";
}

function audioExtension(mimeType: string): string {
  if (mimeType.includes("mp4")) return "m4a";
  if (mimeType.includes("ogg")) return "ogg";
  return "webm";
}

async function loadCart() {
  try {
    applyCart(await api.value.getCart());
  } catch (error) {
    applyCart({ items: [], total_quantity: 0, subtotal_amount: 0 });
  }
}

async function loadCollections(force = false) {
  if (lazyLoaded.collections && !force) return;
  const results = await Promise.allSettled([
    api.value.listUserProducts("favorite"),
    api.value.listUserProducts("compare"),
    api.value.listUserProducts("recent"),
  ]);
  if (results[0].status === "fulfilled") collections.favorite = results[0].value;
  if (results[1].status === "fulfilled") collections.compare = results[1].value;
  if (results[2].status === "fulfilled") collections.recent = results[2].value;
  lazyLoaded.collections = true;
}

async function loadCollectionsOnce() {
  await loadCollections(false);
}

async function refreshSecondaryAfterTurn() {
  const tasks: Array<Promise<unknown>> = [];
  if (lazyLoaded.collections) tasks.push(loadCollections(true));
  if (lazyLoaded.ops) tasks.push(loadMetrics(), loadDashboard());
  if (tasks.length) await Promise.allSettled(tasks);
}

function setCollectionTab(tab: CollectionListType) {
  collectionTab.value = tab;
  void loadCollectionsOnce();
}

function setActiveTab(tab: "trace" | "health" | "ops" | "raw") {
  activeTab.value = tab;
  if (tab === "health") {
    void Promise.allSettled([
      lazyLoaded.deepHealth ? Promise.resolve() : loadHealth(true),
      lazyLoaded.voice ? Promise.resolve() : loadVoiceCapabilities(),
    ]);
  }
  if (tab === "ops") {
    void Promise.allSettled([loadMetrics(), loadDashboard()]);
  }
}

function applyCart(payload: CartState) {
  cart.items = Array.isArray(payload.items) ? payload.items : [];
  cart.total_quantity = Number(payload.total_quantity || 0);
  cart.subtotal_amount = Number(payload.subtotal_amount || 0);
}

async function addToCart(card: ProductCardData) {
  const productId = productIdOf(card);
  if (!productId) return notify("商品缺少 product_id");
  try {
    await api.value.addCartItem(productId, 1, composer.value);
    await loadCart();
    notify("已加入购物车");
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

async function toggleCollection(listType: CollectionListType, productId: string) {
  if (!productId) return notify("商品缺少 product_id");
  try {
    const exists = collections[listType].some((item) => productIdOf(item.product) === productId);
    if (exists) {
      await api.value.removeUserProduct(listType, productId);
      collections[listType] = collections[listType].filter((item) => productIdOf(item.product) !== productId);
      notify(`${collectionLabel(listType)}已移除`);
    } else {
      await api.value.addUserProduct(listType, productId);
      await loadCollections(true);
      notify(`已加入${collectionLabel(listType)}`);
    }
    if (lazyLoaded.ops) void loadDashboard();
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

async function searchVisionCandidate(candidate: VisionObjectCandidate) {
  const query = candidate.search_query || candidate.label;
  if (!lastVisionUploadId.value) {
    composer.value = query;
    return notify("图片已清空，请重新上传后再按主体图搜");
  }
  try {
    const result = await api.value.imageSearchUpload(lastVisionUploadId.value, query, parsePreference());
    visionPanel.value = result.vision_analysis || visionPanel.value;
    trace.value = Array.isArray(result.trace) ? result.trace : [];
    messages.value.push({
      id: `local-vision-${Date.now()}`,
      role: "assistant",
      content: `已按“${candidate.label}”重新图搜。`,
      productCards: result.product_cards || [],
    });
    scrollMessagesToBottom();
    await Promise.allSettled([loadCollections(true)]);
    void refreshSecondaryAfterTurn();
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

async function buyNow(card: ProductCardData) {
  const productId = productIdOf(card);
  if (!productId) return notify("商品缺少 product_id");
  try {
    checkoutPreview.value = await api.value.previewCheckout([{ product_id: productId, quantity: 1 }]);
    notify("结算快照已生成");
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

async function previewCartCheckout() {
  try {
    checkoutPreview.value = await api.value.previewCheckout();
    notify("购物车结算快照已生成");
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

async function confirmCheckout() {
  if (!checkoutPreview.value) return;
  try {
    const order = await api.value.confirmCheckout(checkoutPreview.value);
    selectedProduct.value = { order };
    checkoutPreview.value = null;
    await loadCart();
    notify(`订单已创建：${order.order_id}`);
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

async function updateCartQuantity(item: CartItem, quantity: number) {
  if (quantity < 1) return removeCartItem(item.cart_item_id);
  try {
    await api.value.updateCartItem(item.cart_item_id, quantity);
    await loadCart();
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

async function removeCartItem(cartItemId: string) {
  try {
    await api.value.removeCartItem(cartItemId);
    await loadCart();
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

async function inspectProduct(card: ProductCardData) {
  const productId = productIdOf(card);
  if (!productId) return notify("商品缺少 product_id");
  try {
    await api.value.markProductView(productId);
    const [detail, intelligence, reviewSummary, questions] = await Promise.allSettled([
      api.value.productDetail(productId),
      api.value.productIntelligence(productId),
      api.value.productReviewSummary(productId),
      api.value.productQuestions(productId),
    ]);
    const detailValue = detail.status === "fulfilled" ? asRecord(detail.value) : {};
    const reviewValue = reviewSummary.status === "fulfilled" ? reviewSummary.value : undefined;
    const questionValue = questions.status === "fulfilled" ? questions.value : undefined;
    productPanel.value = {
      product_id: productId,
      title: String(detailValue.title || card.title || productId),
      category: String(detailValue.category || card.category || ""),
      price: Number(detailValue.price ?? card.price ?? 0),
      rating: Number(detailValue.rating ?? card.rating ?? 0),
      sales: Number(detailValue.sales ?? card.sales ?? 0),
      stock: Number(detailValue.stock ?? card.stock ?? 0),
      image_url: String(detailValue.image_url || card.image_url || ""),
      description: String(detailValue.description || card.subtitle || ""),
      reviewSummary: reviewValue,
      questions: questionValue,
      detail: detailValue,
      intelligence: intelligence.status === "fulfilled" ? asRecord(intelligence.value) : {},
    };
    selectedProduct.value = {
      detail: detail.status === "fulfilled" ? detail.value : asErrorMessage(detail.reason),
      intelligence: intelligence.status === "fulfilled" ? intelligence.value : asErrorMessage(intelligence.reason),
      reviewSummary: reviewSummary.status === "fulfilled" ? reviewSummary.value : asErrorMessage(reviewSummary.reason),
      questions: questions.status === "fulfilled" ? questions.value : asErrorMessage(questions.reason),
    };
    activeTab.value = "raw";
    await Promise.allSettled([loadCollections(true)]);
    if (lazyLoaded.ops) void loadDashboard();
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

async function submitProductQuestion() {
  if (!productPanel.value || !questionDraft.value) return;
  try {
    await api.value.createProductQuestion(productPanel.value.product_id, questionDraft.value);
    questionDraft.value = "";
    productPanel.value.questions = await api.value.productQuestions(productPanel.value.product_id);
    notify("问题已提交");
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

async function sendFeedback(messageId: string, rating: 1 | -1, reason = "") {
  try {
    await api.value.feedback(messageId, rating, reason);
    notify("反馈已记录");
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

async function loadProfile() {
  try {
    const profile = await api.value.getProfile();
    if (profile && typeof profile === "object") {
      preferenceText.value = stringifyPretty(profile);
    }
  } catch {
    // Profile can be empty in a fresh database.
  }
}

async function savePreference() {
  try {
    await api.value.savePreference(parsePreference());
    notify("偏好已保存");
  } catch (error) {
    notify(asErrorMessage(error));
  }
}

function parsePreference(): Record<string, unknown> {
  try {
    const parsed = JSON.parse(preferenceText.value || "{}");
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function collectionLabel(listType: CollectionListType): string {
  return collectionTabs.find((tab) => tab.id === listType)?.label || listType;
}

function numberMetric(value: unknown): string {
  const number = Number(value || 0);
  return Number.isFinite(number) ? String(Math.round(number * 100) / 100) : "0";
}

function percent(value: number): string {
  if (!Number.isFinite(value)) return "0%";
  return `${Math.round(value * 1000) / 10}%`;
}

function funnelWidth(count: number): number {
  const rows = dashboard.value?.funnel || [];
  const maxCount = Math.max(...rows.map((item) => Number(item.count || 0)), 1);
  return Math.max(Math.round((Number(count || 0) / maxCount) * 100), count > 0 ? 4 : 0);
}

function notify(message: string) {
  toast.value = message;
  window.setTimeout(() => {
    if (toast.value === message) toast.value = "";
  }, 3200);
}

function scrollMessagesToBottom() {
  nextTick(() => {
    const node = messageScrollRef.value;
    if (node) node.scrollTop = node.scrollHeight;
  });
}
</script>

<style scoped>
.panel {
  @apply rounded-lg border border-slate-200/80 bg-white/90 shadow-sm backdrop-blur;
}

.section-title {
  @apply text-sm font-semibold text-slate-950;
}

.field-label {
  @apply block text-xs font-semibold uppercase tracking-normal text-slate-500;
}

.field-input,
.field-textarea {
  @apply mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm transition placeholder:text-slate-400 hover:border-slate-300 focus:border-teal-600 focus:ring-0;
}

.field-textarea {
  @apply resize-none leading-6;
}

.btn-primary {
  @apply inline-flex items-center justify-center gap-2 rounded-lg bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-800 active:scale-[0.99] disabled:cursor-not-allowed disabled:bg-slate-300;
}

.btn-secondary {
  @apply inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 active:scale-[0.99];
}

.icon-btn,
.icon-btn-sm {
  @apply inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 active:scale-[0.98];
}

.icon-btn {
  @apply h-9 min-w-9 px-2;
}

.icon-btn-sm {
  @apply h-7 min-w-7 px-1.5;
}

.action-btn {
  @apply inline-flex h-9 items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2 text-xs font-semibold text-slate-700 transition hover:border-teal-300 hover:bg-teal-50 hover:text-teal-800 active:scale-[0.98];
}

.badge {
  @apply inline-flex items-center rounded-lg bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600;
}

.chip {
  @apply inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-teal-300 hover:bg-teal-50 hover:text-teal-800;
}

.empty-state {
  @apply flex flex-col items-center gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50/70 px-4 py-6 text-center text-sm text-slate-500;
}

.json-box {
  @apply max-h-[520px] overflow-auto rounded-lg border border-slate-200 bg-slate-950 p-3 text-xs leading-5 text-slate-100;
}
</style>
