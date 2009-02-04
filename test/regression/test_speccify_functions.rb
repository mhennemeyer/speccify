require File.dirname(__FILE__) + "/../test_helper.rb"

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
  
  describe "#make_constantizeable(string)" do
    it "returns arg if arg is not a string" do
      Speccify::Functions.make_constantizeable(1).should == 1
    end
    
    it "removes nonword chars" do
      Speccify::Functions.make_constantizeable("@hello").should == "hello"
    end
    
    it "removes leading numbers" do
      Speccify::Functions.make_constantizeable("11_hello").should == "_hello"
    end
    
    it "doesn't remove inline whitespace" do
      Speccify::Functions.make_constantizeable("h e l l o").should == "h e l l o"
    end
    
    it "removes leading whitespace" do
      Speccify::Functions.make_constantizeable(" hello").should == "hello"
      Speccify::Functions.make_constantizeable("1 hello").should == "hello"
      Speccify::Functions.make_constantizeable("1 1 @ hello").should == "hello"
    end
  end
end