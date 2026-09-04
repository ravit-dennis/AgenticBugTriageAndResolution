function parsePagination({ limit = 3, offset = 0 } = {}) {
  const parsedLimit = Number.parseInt(limit, 10);
  const parsedOffset = Number.parseInt(offset, 10);

  return {
    limit: Number.isNaN(parsedLimit) ? 3 : parsedLimit,
    offset: Number.isNaN(parsedOffset)
      ? 0
      : parsedOffset * (Number.isNaN(parsedLimit) ? 3 : parsedLimit),
  };
}

module.exports = { parsePagination };
