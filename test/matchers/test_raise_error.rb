require File.dirname(__FILE__) + "/../test_helper.rb"

describe "raise_error" do
  
  describe "with no argument given" do
    it "passes if there was an error" do
      lambda {nonexisting}.should raise_error
    end
    
    it "fails if there was no error" do
      lambda do
        lambda { 1 }.should raise_error
      end.should raise_error
    end
  end
  
  describe "with string argument given" do
    
    it "passes if there was an error with a message that eqls the string arg" do
      lambda {raise "message"}.should raise_error("message")
    end
    
    it "fails if there was no error" do
      lambda do
        lambda { 1 }.should raise_error("message")
      end.should raise_error
    end
    
    it "fails if there was an error with a message that doesn't eqls the string arg" do
      lambda do
        lambda { raise "other message" }.should raise_error("message")
      end.should raise_error
    end
  end
  
  describe "with regexp argument given" do
    
    it "passes if there was an error with a message that matches the regexp arg" do
      lambda {raise "message"}.should raise_error(/essa/)
    end
    
    it "fails if there was no error" do
      lambda do
        lambda { 1 }.should raise_error(/essa/)
      end.should raise_error
    end
    
    it "fails if there was an error with a message that doesn't match the regexp arg" do
      lambda do
        lambda { raise "other" }.should raise_error(/essa/)
      end.should raise_error
    end
  end
  
end