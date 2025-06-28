// client/git-integration/tests/gitUtils.spec.js

import { describe, it, expect } from "vitest";
import {
  getStatusLabel,
  getFileStatusClass,
  getCommitFileStatusClass,
  getLogLevelBgClass,
  getLogLevelTextColorClass,
} from "../gitUtils.js";

describe("gitUtils.js", () => {
  describe("getStatusLabel", () => {
    it("should return correct labels for known status characters", () => {
      expect(getStatusLabel("A")).toBe("Added");
      expect(getStatusLabel("M")).toBe("Modified");
      expect(getStatusLabel("D")).toBe("Deleted");
      expect(getStatusLabel("R")).toBe("Renamed");
      expect(getStatusLabel("C")).toBe("Copied");
      expect(getStatusLabel("U")).toBe("Unmerged");
      expect(getStatusLabel("?")).toBe("Untracked");
    });

    it("should return the input character for an unknown status", () => {
      expect(getStatusLabel("X")).toBe("X");
    });
  });

  // Test suite for the getFileStatusClass function
  describe("getFileStatusClass", () => {
    it("should prioritize index status for staged files", () => {
      // Staged Addition
      expect(getFileStatusClass("A", " ")).toContain("bg-green-100");
      // Staged Modification
      expect(getFileStatusClass("M", " ")).toContain("bg-blue-100");
    });

    it("should use work-tree status for unstaged files", () => {
      // Unstaged Modification
      expect(getFileStatusClass(" ", "M")).toContain("bg-blue-100");
      // Unstaged Deletion
      expect(getFileStatusClass(" ", "D")).toContain("bg-red-100");
    });

    it("should return correct class for untracked files", () => {
      // An untracked file has '?' in both index and work-tree status
      expect(getFileStatusClass("?", "?")).toContain("bg-gray-200");
    });

    it("should return danger class for unmerged (conflicted) files", () => {
      expect(getFileStatusClass("U", "U")).toContain("border-red-500");
      expect(getFileStatusClass("U", "U")).toContain("bg-red-100");
    });
  });

  // Test suite for getCommitFileStatusClass
  describe("getCommitFileStatusClass", () => {
    it("should return correct classes for commit file statuses", () => {
      expect(getCommitFileStatusClass("A")).toContain("bg-green-100");
      expect(getCommitFileStatusClass("M")).toContain("bg-blue-100");
      expect(getCommitFileStatusClass("D")).toContain("bg-red-100");
      expect(getCommitFileStatusClass("R")).toContain("bg-yellow-100");
      expect(getCommitFileStatusClass("C")).toContain("bg-purple-100");
    });

    it("should handle complex statuses like 'M100' by looking at the first char", () => {
      expect(getCommitFileStatusClass("M100")).toContain("bg-blue-100");
    });

    it("should return a default class for an unknown status", () => {
      expect(getCommitFileStatusClass("X")).toContain("bg-gray-200");
    });
  });

  // Test suite for log level background colors
  describe("getLogLevelBgClass", () => {
    it("should return correct background color classes for each log level", () => {
      expect(getLogLevelBgClass("success")).toBe("bg-green-500");
      expect(getLogLevelBgClass("error")).toBe("bg-red-500");
      expect(getLogLevelBgClass("warn")).toBe("bg-yellow-500");
      expect(getLogLevelBgClass("info")).toBe("bg-blue-500");
      expect(getLogLevelBgClass("all")).toBe("bg-gray-500");
    });

    it("should return a default gray background for an unknown level", () => {
      expect(getLogLevelBgClass("debug")).toBe("bg-gray-400");
    });
  });

  // Test suite for log level text colors
  describe("getLogLevelTextColorClass", () => {
    it("should return correct text color classes for each log level", () => {
      expect(getLogLevelTextColorClass("success")).toContain("text-green-600");
      expect(getLogLevelTextColorClass("error")).toContain("text-red-600");
      expect(getLogLevelTextColorClass("warn")).toContain("text-yellow-600");
      expect(getLogLevelTextColorClass("info")).toContain("text-blue-600");
      expect(getLogLevelTextColorClass("all")).toContain("text-gray-600");
    });

    it("should return a default gray text color for an unknown level", () => {
      expect(getLogLevelTextColorClass("debug")).toBe("text-gray-400");
    });
  });
});
