const path = require("path");

function parseBoolean(value, fallback) {
  if (value === undefined) {
    return fallback;
  }

  return value.toLowerCase() === "true";
}

function databaseConfig(environment, defaults) {
  const prefix = environment.toUpperCase();
  const dialect = process.env[`${prefix}_DB_DIALECT`] || defaults.dialect;
  const config = {
    dialect,
    logging: parseBoolean(process.env[`${prefix}_DB_LOGGING`], false),
  };

  if (dialect === "sqlite") {
    return {
      ...config,
      storage:
        process.env[`${prefix}_DB_STORAGE`] ||
        path.resolve(__dirname, "..", defaults.storage),
    };
  }

  return {
    ...config,
    username: process.env[`${prefix}_DB_USERNAME`],
    password: process.env[`${prefix}_DB_PASSWORD`],
    database: process.env[`${prefix}_DB_NAME`],
    host: process.env[`${prefix}_DB_HOSTNAME`] || "127.0.0.1",
  };
}

/** @type {Record<string, import('sequelize').Options>} */
module.exports = {
  development: databaseConfig("development", {
    dialect: "sqlite",
    storage: "data/development.sqlite",
  }),
  test: databaseConfig("test", {
    dialect: "sqlite",
    storage: "data/test.sqlite",
  }),
  production: databaseConfig("production", {
    dialect: "postgres",
  }),
};
