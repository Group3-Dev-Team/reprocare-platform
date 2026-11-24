import { describe, expect, it } from "vitest";
import { respond } from "../pages/AssistantPage";

describe("health assistant matching", () => {
  it("recognises emergencies before anything else", () => {
    expect(respond("I have heavy bleeding during pregnancy").kind).toBe(
      "urgent",
    );
    expect(respond("damu nyingi").kind).toBe("urgent");
  });
  it("refuses personal medical questions", () => {
    expect(respond("Do I have an infection?").kind).toBe("personal");
  });
  it("matches English and Kiswahili topics", () => {
    expect(respond("What happens at a first antenatal visit?")).toEqual({
      kind: "answer",
      id: "antenatal",
    });
    expect(respond("nina mimba, niende wapi")).toEqual({
      kind: "answer",
      id: "antenatal",
    });
  });
  it("keeps family planning separate from fertility consultations in Kiswahili", () => {
    expect(respond("Kuna njia gani za uzazi wa mpango?").id).toBe(
      "contraception",
    );
    expect(
      respond("Nitarajie nini katika ushauri wangu wa kwanza wa uzazi?").id,
    ).toBe("fertility");
  });
  it('does not match "anc" inside "cancer"', () => {
    expect(respond("cancer").id).not.toBe("antenatal");
  });
  it("admits when it has no reviewed answer", () => {
    expect(respond("how do I fix my car").kind).toBe("unknown");
  });
});
