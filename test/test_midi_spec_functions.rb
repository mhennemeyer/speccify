require File.dirname(__FILE__) + "/test_helper.rb"

describe MidiSpec::Functions do
  
  describe "determine_class_name(name)" do
    it "Horst -> Horst" do
      MidiSpec::Functions::determine_class_name("Horst").should == "Horst"
    end
    
    it "HorstTest -> HorstTest" do
      MidiSpec::Functions::determine_class_name("HorstTest").should == "HorstTest"
    end
    
    it "HorstTest Hello -> HorstTestHello" do
      MidiSpec::Functions::determine_class_name("HorstTest Hello").should == "HorstTestHello"
    end
    
    it "Horst test hello -> HorstTestHello" do
      MidiSpec::Functions::determine_class_name("Horst test hello").should == "HorstTestHello"
    end
  end
end