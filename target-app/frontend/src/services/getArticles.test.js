import axios from "axios";
import { beforeEach, describe, expect, test, vi } from "vitest";
import getArticles from "./getArticles";

vi.mock("axios", () => ({
  default: vi.fn(),
}));

describe("getArticles pagination contract", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    axios.mockResolvedValue({ data: { articles: [], articlesCount: 0 } });
  });

  test("converts the selected page into a record offset", async () => {
    const headers = { Authorization: "Token test" };

    await getArticles({
      headers,
      limit: 3,
      location: "global",
      page: 2,
    });

    expect(axios).toHaveBeenCalledWith({
      headers,
      url: "api/articles?limit=3&&offset=6",
    });
  });
});
