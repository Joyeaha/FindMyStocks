/**
 * 股票评分计算模块
 * 根据股票的基本面数据计算综合评分
 */

(function () {
  "use strict";

  /**
   * 计算股票评分
   * @param {Array} stocks - 股票数据数组（以 label 为 key）
   * @returns {Array} 包含评分信息的股票数组
   */
  function calculateRating(stocks) {
    console.log(stocks);
    return stocks.map((stock) => {
      let rating = 0;

      // 尝试通过 label 获取数据，如果不存在则尝试通过 key 获取（向后兼容）
      const getValue = (label, key) => {
        // 先尝试通过 label 获取
        if (stock[label] !== undefined && stock[label] !== null) {
          return stock[label];
        }
        // 再尝试通过 key 获取（向后兼容）
        if (stock[key] !== undefined && stock[key] !== null) {
          return stock[key];
        }
        return null;
      };

      // 获取数据（优先使用 label，如果没有则使用 key）
      // PE-TTM 对应的 label 可能是 "PE-TTM" 或其他
      const peTtm = parseFloat(getValue("PE-TTM", "pe_ttm")) || 0;
      // PB 对应的 label 可能是 "PB" 或其他
      const pb = parseFloat(getValue("PB", "pb")) || 0;
      // 股息率对应的 label 可能是 "股息率"、"DYR" 或其他
      const dyr =
        parseFloat(getValue("股息率", "dyr") || getValue("DYR", "dyr")) || 0;

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
