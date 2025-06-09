// client/utils/gitUtils.js

export function getStatusLabel(statusChar) {
  const map = {
    A: "Added",
    M: "Modified",
    D: "Deleted",
    R: "Renamed",
    C: "Copied",
    "?": "Untracked",
  };
  return map[statusChar] || statusChar;
}

export function getFileStatusClass(index, workTree) {
  const status = index !== " " && index !== "?" ? index : workTree;
  if (status === "A" || status === "C")
    return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
  if (status === "M")
    return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
  if (status === "D")
    return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
  if (status === "R")
    return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
  if (status === "?")
    return "bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
  return "bg-gray-200 text-black";
}

export function getCommitFileStatusClass(statusChar) {
  const status = statusChar.charAt(0); // Handle statuses like 'M100'
  if (status === "A")
    return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
  if (status === "M")
    return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
  if (status === "D")
    return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
  return "bg-gray-200 text-black";
}

export function getLogLevelBgClass(level) {
  const map = {
    success: "bg-green-500",
    error: "bg-red-500",
    warn: "bg-yellow-500",
    info: "bg-blue-500",
    all: "bg-gray-500",
  };
  return map[level] || "bg-gray-400";
}

export function getLogLevelTextColorClass(level) {
  const map = {
    success: "text-green-600 dark:text-green-400",
    error: "text-red-600 dark:text-red-400",
    warn: "text-yellow-600 dark:text-yellow-400",
    info: "text-blue-600 dark:text-blue-400",
    all: "text-gray-600 dark:text-gray-400",
  };
  return map[level] || "text-gray-400";
}
