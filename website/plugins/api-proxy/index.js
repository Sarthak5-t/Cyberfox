/**
 * Docusaurus plugin to proxy /api/* requests to the auth dev server.
 * Only activates in development mode (docusaurus start).
 */
module.exports = function (context) {
  return {
    name: 'api-proxy',
    configureWebpack(config, isServer, utils) {
      // Only apply to the client-side webpack dev server
      if (isServer) return {};
      return {
        devServer: {
          proxy: [
            {
              context: ['/api'],
              target: 'http://localhost:4001',
              changeOrigin: true,
            },
          ],
        },
      };
    },
  };
};
