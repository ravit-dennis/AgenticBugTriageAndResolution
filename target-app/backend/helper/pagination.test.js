const { parsePagination } = require("./pagination");

describe("parsePagination", () => {
  test("uses API offset as the number of records to skip", () => {
    expect(parsePagination({ limit: "10", offset: "20" })).toEqual({
      limit: 10,
      offset: 20,
    });
  });

  test("uses safe defaults for invalid input", () => {
    expect(parsePagination({ limit: "invalid", offset: "invalid" })).toEqual({
      limit: 3,
      offset: 0,
    });
  });
});
