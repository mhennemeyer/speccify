require File.dirname(__FILE__) + "/test_helper.rb"

describe Speccify::Functions do
  
  describe "determine_class_name(name)" do
    it "Horst -> Horst" do
      Speccify::Functions::determine_class_name("Horst").should == "Horst"
    end
    
    it "HorstTest -> HorstTest" do
      Speccify::Functions::determine_class_name("HorstTest").should == "HorstTest"
    end
    
    it "HorstTest Hello -> HorstTestHello" do
      Speccify::Functions::determine_class_name("HorstTest Hello").should == "HorstTestHello"
    end
    
    it "Horst test hello -> HorstTestHello" do
      Speccify::Functions::determine_class_name("Horst test hello").should == "HorstTestHello"
    end
  end
  
  describe "#build_matcher(matcher_name, args, &block)" do
  end
end