#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    uint8_t *data;
    size_t   capacity;
    size_t   bit_pos;
} BitWriter;

static int bw_init(BitWriter *bw, size_t initial_bytes)
{
    bw->data = (uint8_t *)calloc(initial_bytes, 1);
    if (!bw->data) return -1;
    bw->capacity = initial_bytes;
    bw->bit_pos = 0;
    return 0;
}

static void bw_free(BitWriter *bw)
{
    free(bw->data);
    bw->data = NULL;
}

static int bw_grow(BitWriter *bw)
{
    size_t new_cap = bw->capacity * 2 + 64;
    uint8_t *p = (uint8_t *)realloc(bw->data, new_cap);
    if (!p) return -1;
    memset(p + bw->capacity, 0, new_cap - bw->capacity);
    bw->data = p;
    bw->capacity = new_cap;
    return 0;
}

static int bw_write_bit(BitWriter *bw, int bit)
{
    if ((bw->bit_pos / 8) >= bw->capacity) {
        if (bw_grow(bw) < 0) return -1;
    }
    if (bit) {
        bw->data[bw->bit_pos / 8] |= (uint8_t)(1u << (7 - bw->bit_pos % 8));
    }
    bw->bit_pos++;
    return 0;
}

typedef struct {
    const uint8_t *data;
    size_t total_bits;
    size_t bit_pos;
} BitReader;

static void br_init(BitReader *br, const uint8_t *data, size_t total_bits)
{
    br->data = data;
    br->total_bits = total_bits;
    br->bit_pos = 0;
}

static int br_read_bit(BitReader *br)
{
    if (br->bit_pos >= br->total_bits) return -1;
    int bit = (br->data[br->bit_pos / 8] >> (7 - br->bit_pos % 8)) & 1;
    br->bit_pos++;
    return bit;
}

static int gamma_write(BitWriter *bw, uint32_t n)
{
    int bits = 0;
    uint32_t tmp = n;
    while (tmp) { bits++; tmp >>= 1; }

    int offset_len = bits - 1;

    for (int i = 0; i < offset_len; i++) {
        if (bw_write_bit(bw, 0) < 0) return -1;
    }
    if (bw_write_bit(bw, 1) < 0) return -1;

    for (int i = offset_len - 1; i >= 0; i--) {
        if (bw_write_bit(bw, (n >> i) & 1) < 0) return -1;
    }
    return 0;
}

static int gamma_read(BitReader *br, uint32_t *out)
{
    int zero_count = 0;
    for (;;) {
        int b = br_read_bit(br);
        if (b < 0) return -1;
        if (b == 1) break;
        zero_count++;
    }
    uint32_t value = 1;
    for (int i = 0; i < zero_count; i++) {
        int b = br_read_bit(br);
        if (b < 0) return -1;
        value = (value << 1) | (uint32_t)b;
    }
    *out = value;
    return 0;
}

static int encode_ids(const int32_t *ids, int count, uint8_t **out, Py_ssize_t *out_len)
{
    if (count == 0) {
        *out = NULL; *out_len = 0;
        return 0;
    }

    BitWriter bw;
    if (bw_init(&bw, (size_t)(count / 2 + 16)) < 0) return -1;

    int32_t prev = 0;
    for (int i = 0; i < count; i++) {
        int32_t delta = ids[i] - prev;
        prev = ids[i];
        if (delta <= 0) delta = 1;
        if (gamma_write(&bw, (uint32_t)delta) < 0) {
            bw_free(&bw);
            return -1;
        }
    }

    size_t bit_count = bw.bit_pos;
    size_t byte_count = (bit_count + 7) / 8;
    size_t total = 4 + 8 + byte_count;

    uint8_t *result = (uint8_t *)malloc(total);
    if (!result) { bw_free(&bw); return -1; }

    uint32_t cnt32 = (uint32_t)count;
    uint64_t bits64 = (uint64_t)bit_count;
    memcpy(result, &cnt32,  4);
    memcpy(result + 4, &bits64, 8);
    memcpy(result + 12, bw.data, byte_count);

    bw_free(&bw);
    *out = result;
    *out_len = (Py_ssize_t)total;
    return 0;
}

static int decode_ids(const uint8_t *encoded, Py_ssize_t encoded_len, int32_t **out_ids, int *out_count)
{
    if (encoded_len == 0 || !encoded) {
        *out_ids = NULL; *out_count = 0;
        return 0;
    }
    if (encoded_len < 12) return -1;

    uint32_t count;
    uint64_t bit_count;
    memcpy(&count, encoded, 4);
    memcpy(&bit_count, encoded + 4, 8);

    int32_t *ids = (int32_t *)malloc(count * sizeof(int32_t));
    if (!ids) return -1;

    BitReader br;
    br_init(&br, encoded + 12, (size_t)bit_count);

    int32_t prev = 0;
    for (uint32_t i = 0; i < count; i++) {
        uint32_t delta;
        if (gamma_read(&br, &delta) < 0) { free(ids); return -1; }
        prev += (int32_t)delta;
        ids[i] = prev;
    }

    *out_ids = ids;
    *out_count = (int)count;
    return 0;
}

static PyObject *py_encode_postings(PyObject *self, PyObject *arg)
{
    if (!PyList_Check(arg)) {
        PyErr_SetString(PyExc_TypeError, "expected list[int]");
        return NULL;
    }

    Py_ssize_t count = PyList_GET_SIZE(arg);

    if (count == 0)
        return PyBytes_FromStringAndSize(NULL, 0);

    int32_t *ids = (int32_t *)malloc((size_t)count * sizeof(int32_t));
    if (!ids) return PyErr_NoMemory();

    for (Py_ssize_t i = 0; i < count; i++) {
        PyObject *item = PyList_GET_ITEM(arg, i);
        long v = PyLong_AsLong(item);
        if (v == -1 && PyErr_Occurred()) { free(ids); return NULL; }
        ids[i] = (int32_t)v;
    }

    uint8_t *buf = NULL;
    Py_ssize_t  buf_len = 0;
    if (encode_ids(ids, (int)count, &buf, &buf_len) < 0) {
        free(ids);
        PyErr_NoMemory();
        return NULL;
    }
    free(ids);

    PyObject *result = PyBytes_FromStringAndSize((char *)buf, buf_len);
    free(buf);
    return result;
}

static PyObject *py_decode_postings(PyObject *self, PyObject *arg)
{
    if (!PyBytes_Check(arg)) {
        PyErr_SetString(PyExc_TypeError, "expected bytes");
        return NULL;
    }

    const uint8_t *encoded  = (const uint8_t *)PyBytes_AS_STRING(arg);
    Py_ssize_t enc_len  = PyBytes_GET_SIZE(arg);

    if (enc_len == 0)
        return PyList_New(0);

    int32_t *ids   = NULL;
    int count = 0;
    if (decode_ids(encoded, enc_len, &ids, &count) < 0) {
        PyErr_SetString(PyExc_ValueError, "decode error");
        return NULL;
    }

    PyObject *list = PyList_New(count);
    if (!list) { free(ids); return NULL; }

    for (int i = 0; i < count; i++) {
        PyObject *item = PyLong_FromLong((long)ids[i]);
        if (!item) { free(ids); Py_DECREF(list); return NULL; }
        PyList_SET_ITEM(list, i, item);
    }

    free(ids);
    return list;
}

static PyMethodDef CgammaMethods[] = {
    {
        "encode_postings",
        py_encode_postings,
        METH_O,
        "encode_postings(ids: list[int]) -> bytes\n"
    },
    {
        "decode_postings",
        py_decode_postings,
        METH_O,
        "decode_postings(data: bytes) -> list[int]\n"
    },
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef cgamma_module = {
    .m_base = PyModuleDef_HEAD_INIT,
    .m_name = "cgamma",
    .m_doc = "doc...",
    .m_size = -1,
    .m_methods = CgammaMethods,
};

PyMODINIT_FUNC PyInit_cgamma(void)
{
    return PyModule_Create(&cgamma_module);
}