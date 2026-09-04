import axios from "axios";
import errorHandler from "../helpers/errorHandler";

// prettier-ignore
async function getArticles({ headers, limit = 3, location, page = 0, tagName, username }) {
  try {
    const offset = page * limit;
    const url = {
      favorites: `api/articles?favorited=${username}&&limit=${limit}&&offset=${offset}`,
      feed: `api/articles/feed?limit=${limit}&&offset=${offset}`,
      global: `api/articles?limit=${limit}&&offset=${offset}`,
      profile: `api/articles?author=${username}&&limit=${limit}&&offset=${offset}`,
      tag: `api/articles?tag=${tagName}&&limit=${limit}&&offset=${offset}`,
    };

    const { data } = await axios({ url: url[location], headers });

    return data;
  } catch (error) {
    errorHandler(error);
  }
}

export default getArticles;
