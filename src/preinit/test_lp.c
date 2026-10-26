/* Host regression test: no root, block devices or phone required.
 * gcc -O2 -Isrc/preinit src/preinit/test_lp.c -o /tmp/test-preinit-lp
 */
#define ioctl test_ioctl
#define main preinit_main
#include "preinit.c"
#undef main
#undef ioctl
#include <assert.h>

static int tables_loaded;

int test_ioctl(int fd, unsigned long request, ...)
{
	(void)fd;
	va_list ap;
	va_start(ap, request);
	struct dm_ioctl *io = va_arg(ap, struct dm_ioctl *);
	va_end(ap);
	if (request == DM_DEV_CREATE) {
		io->dev = makedev(253, 7);
	} else if (request == DM_TABLE_LOAD) {
		assert(io->target_count == 3);
		struct dm_target_spec *t = (void *)((char *)io + io->data_start);
		assert(t->sector_start == 0 && t->length == 8);
		assert(!strcmp(t->target_type, "linear"));
		assert(!strcmp((char *)(t + 1), "259:8 2048"));
		t = (void *)((char *)t + t->next);
		assert(t->sector_start == 8 && t->length == 16);
		assert(!strcmp(t->target_type, "linear"));
		assert(!strcmp((char *)(t + 1), "259:9 4096"));
		t = (void *)((char *)t + t->next);
		assert(t->sector_start == 24 && t->length == 4);
		assert(!strcmp(t->target_type, "zero"));
		tables_loaded++;
	} else {
		assert(request == DM_DEV_SUSPEND);
	}
	return 0;
}

int main(void)
{
	assert(sizeof(struct lp_extent) == 24);
	assert(sizeof(struct lp_block_device) == 64);
	const char sources[2][32] = { "259:8", "259:9" };
	struct lp_extent ext[] = {
		{ .num_sectors = 8, .target_type = 0, .target_data = 2048, .target_source = 0 },
		{ .num_sectors = 16, .target_type = 0, .target_data = 4096, .target_source = 1 },
		{ .num_sectors = 4, .target_type = 1 },
	};
	unsigned mn;
	assert(!dm_create_linear("system", 1, sources, 2, ext, 3, &mn));
	assert(mn == 7 && tables_loaded == 1);
	ext[1].target_source = 2;
	assert(dm_create_linear("system", 1, sources, 2, ext, 3, &mn) == -1);
	ext[1].target_source = 1;
	ext[1].target_type = 3;
	assert(dm_create_linear("system", 1, sources, 2, ext, 3, &mn) == -1);
	ext[1].target_type = 0;
	const char missing[2][32] = { "259:8", "" };
	assert(dm_create_linear("system", 1, missing, 2, ext, 3, &mn) == -1);
	assert(tables_loaded == 1);
	puts("PASS: retrofit LP sources, zero extents and invalid-source rejection");
	return 0;
}
