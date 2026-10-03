// 在 commit 訊息尾端加一行 vanity-nonce，找出 SHA-1 以指定十六進位前綴開頭的 commit。
// 從 stdin 讀 `git cat-file commit HEAD` 的內容，輸出加上 nonce 的新內容；
// 結果仍是真實的 git commit 物件，可用 `git hash-object -t commit` 驗證。
// 用法：vanity_commit <hex 前綴> [執行緒數] < commit > new_commit
#define OPENSSL_SUPPRESS_DEPRECATED
#include <openssl/sha.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define NONCE_LINE "vanity-nonce: "
#define NONCE_DIGITS 16

static unsigned char want[20];
static int want_nibbles;
static SHA_CTX base_ctx;
static int threads;
// 目前找到的最小 nonce；每個執行緒由小到大搜尋，超過它就停止，結果因此固定可重現。
static _Atomic unsigned long long best = ~0ULL;

static int matches(const unsigned char *digest) {
    for (int i = 0; i < want_nibbles; i++) {
        unsigned char got = (i % 2) ? (digest[i / 2] & 0x0f) : (digest[i / 2] >> 4);
        unsigned char exp = (i % 2) ? (want[i / 2] & 0x0f) : (want[i / 2] >> 4);
        if (got != exp)
            return 0;
    }
    return 1;
}

static void *search(void *arg) {
    unsigned long long nonce = (unsigned long long)(size_t)arg;
    char tail[NONCE_DIGITS + 2];
    unsigned char digest[20];
    for (; nonce < atomic_load_explicit(&best, memory_order_relaxed); nonce += threads) {
        snprintf(tail, sizeof(tail), "%016llx\n", nonce);
        SHA_CTX ctx = base_ctx;
        SHA1_Update(&ctx, tail, NONCE_DIGITS + 1);
        SHA1_Final(digest, &ctx);
        if (matches(digest)) {
            unsigned long long cur = atomic_load(&best);
            while (nonce < cur && !atomic_compare_exchange_weak(&best, &cur, nonce))
                ;
            break;
        }
    }
    return NULL;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "用法：%s <hex 前綴> [執行緒數] < commit\n", argv[0]);
        return 2;
    }
    const char *prefix = argv[1];
    want_nibbles = (int)strlen(prefix);
    if (want_nibbles < 1 || want_nibbles > 16 || strspn(prefix, "0123456789abcdef") != (size_t)want_nibbles) {
        fprintf(stderr, "前綴必須是 1 到 16 個小寫十六進位字元\n");
        return 2;
    }
    for (int i = 0; i < want_nibbles; i++) {
        unsigned char v = (unsigned char)(prefix[i] <= '9' ? prefix[i] - '0' : prefix[i] - 'a' + 10);
        want[i / 2] |= (i % 2) ? v : (unsigned char)(v << 4);
    }
    threads = argc > 2 ? atoi(argv[2]) : (int)sysconf(_SC_NPROCESSORS_ONLN);
    if (threads < 1)
        threads = 1;

    static char body[1 << 20];
    size_t len = fread(body, 1, sizeof(body) - 64, stdin);
    if (len == 0 || !feof(stdin)) {
        fprintf(stderr, "讀不到 commit 內容，或內容過大\n");
        return 1;
    }
    // 已經有 nonce 的 commit 不再疊加。
    if (strstr(body, "\n" NONCE_LINE)) {
        fprintf(stderr, "commit 已含 vanity-nonce\n");
        return 1;
    }
    if (body[len - 1] != '\n')
        body[len++] = '\n';
    len += (size_t)sprintf(body + len, "\n" NONCE_LINE);
    size_t total = len + NONCE_DIGITS + 1;

    char header[32];
    int header_len = snprintf(header, sizeof(header), "commit %zu", total) + 1;
    SHA1_Init(&base_ctx);
    SHA1_Update(&base_ctx, header, (size_t)header_len);
    SHA1_Update(&base_ctx, body, len);

    pthread_t *workers = calloc((size_t)threads, sizeof(*workers));
    for (int i = 0; i < threads; i++)
        pthread_create(&workers[i], NULL, search, (void *)(size_t)i);
    for (int i = 0; i < threads; i++)
        pthread_join(workers[i], NULL);

    fwrite(body, 1, len, stdout);
    printf("%016llx\n", atomic_load(&best));
    return 0;
}
