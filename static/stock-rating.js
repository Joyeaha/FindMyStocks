/**
 * 股票评分计算模块
 * 根据股票的基本面数据计算综合评分
 */

(function () {
  "use strict";

  /**
   * 计算股票评分
   * @param {Array} stocks - 股票数据数组
   * @returns {Array} 包含评分信息的股票数组
   */
  function calculateRating(stocks) {
    console.log(stocks);
    return stocks.map((stock) => {
      let rating = 0;

      // 获取数据
      const peTtm = parseFloat(stock.pe_ttm) || 0;
      const pb = parseFloat(stock.pb) || 0;
      const dyr = parseFloat(stock.dyr) || 0;

      // 市盈率TTM评分（0-15为优秀）
      if (peTtm > 0 && peTtm <= 15) {
        rating += 10;
      } else if (peTtm > 15 && peTtm <= 25) {
        rating += 5;
      } else if (peTtm > 0) {
        rating -= 5;
      }

      // 市净率PB评分（0-2为优秀）
      if (pb > 0 && pb <= 2) {
        rating += 10;
      } else if (pb > 2 && pb <= 3) {
        rating += 5;
      } else if (pb > 0) {
        rating -= 5;
      }

      // 股息率评分（>3%为优秀）
      if (dyr >= 3) {
        rating += 10;
      } else if (dyr > 0) {
        rating += 5;
      }

      // 获取股票名称
      const stockName = stock.stockName;

      return {
        ...stock,
        stockName: stockName,
        rating: rating,
      };
    });
  }

  // 暴露到全局
  if (typeof window !== "undefined") {
    window.calculateRating = calculateRating;
  }
})();
